"""
mcp_openai_client.py - MCP client for OpenAI API interactions.
"""

import os
import json
import asyncio
from contextlib import AsyncExitStack
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from dotenv import load_dotenv
from anyio import ClosedResourceError

load_dotenv()

SYSTEM_PROMPT = """ You are an Integlligent IBM Maximo Assistant. You Help users
query and understand data from IBM Maximo. You can answer questions about work orders, assets, locations, and more.
You can also provide insights and recommendations based on the data you have access to.

You have access to the following tools:
1. search_work_orders: Fetch Work Orders from Maximo based on status, site, and other criteria.
2. get_work_order_details: Get detailed information about a specific work order by its ID.

When answering questions:
1. Use the appropriate tool to fetch data from Maximo.
2. Present the data in a clear and readable format.
3. Provide insights, summeries and recommendations when appropriate.
4. If query returns no data, inform the user and suggest alternative queries or actions they can take.
5. Always strive to provide accurate and helpful information based on the data you have access to.
6. ALways be honest about what you know and don't know. If you don't have access to certain information, let the user know and suggest how they might find it.
7. Always mention the record number in your response.

This read only assistant, it cannot update or change any data in Maximo. It can only fetch and present information to the user.

"""

class MaximoMCPClient:
    def __init__(self):
        self.openai = AsyncOpenAI()
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.tools = []



    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["maximo_mcp_server.py"],
            env=None
        )
        stdio_transport=await self.exit_stack.enter_async_context(
            stdio_client(server_params)
            )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await self.session.initialize()

        response = await self.session.list_tools()
        self.tools = []
        for tool in response.tools:
            try:
                tool_dict = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": getattr(tool, 'inputSchema', {
                            "type": "object",
                            "properties": {}
                        })
                    }
                }
                self.tools.append(tool_dict)
            except AttributeError as e:
                print(f"Error processing tool: {e}, tool object: {tool}", file=sys.stderr, flush=True)
                raise
        
        tool_names = [tool['function']['name'] for tool in self.tools]
        print(f"Connected to Maximo MCP Server. Available tools: {tool_names}")
        

    async def process_query(self, query: str,
                            conversation_history: list = None) -> tuple:
        """Process user query using OpenAI API and Maximo tools.
        
        Returns:
            tuple: (response_text, reasoning_dict)
        """
        if conversation_history is None:
            conversation_history = []

        # Initialize reasoning tracker
        reasoning = {
            "query": query,
            "tools_used": [],
            "steps": [],
            "tool_results": []
        }

        message = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history + [{"role": "user", "content": query}]
        reasoning["steps"].append(f"Query received: {query}")

        response = await self.openai.chat.completions.create(
            model="gpt-5-mini",
            messages=message,
            tools=self.tools,
            max_completion_tokens=4096
        )

        while response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls
            
            # Save the assistant's response containing the tool call to history
            message.append(response.choices[0].message)

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Track tool usage
                tool_info = {"name": tool_name, "args": tool_args}
                reasoning["tools_used"].append(tool_info)
                reasoning["steps"].append(f"Calling tool: {tool_name}")
                
                print(f"Tool use detected: {tool_name} with args {tool_args}", file=sys.stderr, flush=True)

                # Execute your Maximo MCP tool
                tool_result = await self.call_tool(tool_name, tool_args)
                result_content = tool_result.content[0].text if tool_result.content else ""
                print(f"Tool result: {result_content}", file=sys.stderr, flush=True)

                # Track tool result
                try:
                    result_json = json.loads(result_content) if result_content.startswith("{") else result_content
                    reasoning["tool_results"].append({
                        "tool": tool_name,
                        "result": result_json
                    })
                except:
                    reasoning["tool_results"].append({
                        "tool": tool_name,
                        "result": result_content
                    })
                
                reasoning["steps"].append(f"Tool result received from {tool_name}")

                # Append tool results using OpenAI format
                message.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_content
                })

            response = await self.openai.chat.completions.create(
                model="gpt-5-mini",
                messages=message,
                tools=self.tools,
                max_completion_tokens=4096
            )

        final_response = response.choices[0].message.content
        reasoning["steps"].append("Final response generated")
        return final_response, reasoning

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a tool on the Maximo MCP server."""
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            return result
        except ClosedResourceError:
            print("MCP transport is closed. Reconnecting to server...")
            await self.cleanup()
            await self.connect_to_server()
            result = await self.session.call_tool(tool_name, tool_args)
            return result

    async def cleanup(self):
        await self.exit_stack.aclose()



