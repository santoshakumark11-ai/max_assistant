import streamlit as st
import asyncio
import sys
import threading
import traceback
from mcp_openai_client import MaximoMCPClient

st.set_page_config(
    page_title="Maximo Q&A Assistant", 
    page_icon="🤖",
    layout="wide")

# Display OpenAI Logo at the top
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.png", width=150, caption="Powered by OpenAI and IBM Maximo")

st.title("🤖 Maximo Q&A Assistant")
st.caption("Ask questions about your Maximo data and get insights in real-time!")

# ALWAYS INITIALIZE AT THE TOP
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.conversation_history = []

#  ---- Sidebar ---------------

with st.sidebar:
    st.header("Configurations")
    st.info("""
    Ensure these are set: \n
    1. Maximo MCP Server is running.
    2. OpenAI API key is configured.   
    3. Maximo API key and base URL are set in the .env file. 
    """)

    st.divider()
    st.subheader("Example Questions")
    exammple_questions = [
        "Show me all APPR work orders?",
        "What is the status of work order 12345?",
        "List all assets at location ADDR2001.",
        "How many work orders are currently in progress at site BEDFORD?",
        "Get detaill of asset 11430",

    ] 
    for q in exammple_questions:
        if st.button(q, use_container_width=True, key=q):
            st.session_state["prefilled_question"] = q

    st.divider()
    if st.button("Clear Chat", use_container_width=True, key="clear_chat"):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.rerun()
    
#  ---- Async Header ---------------

def get_async_loop():
    if "_async_loop" not in st.session_state or st.session_state._async_loop.is_closed():
        loop = asyncio.new_event_loop()
        started = threading.Event()

        def start_loop():
            asyncio.set_event_loop(loop)
            started.set()
            loop.run_forever()

        thread = threading.Thread(target=start_loop, daemon=True)
        thread.start()
        started.wait()
        st.session_state._async_loop = loop
        st.session_state._async_thread = thread
        st.session_state.mcp_client = None
    return st.session_state._async_loop


def run_async(coro):
    """Run an async coroutine from sync Streamlit context."""
    loop = get_async_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


# --- Initialize MCP Client ---------------
def get_mcp_client():
    client = st.session_state.get("mcp_client")
    if client is not None:
        session = getattr(client, "session", None)
        if session is not None and hasattr(session, "_write_stream"):
            try:
                if session._write_stream.is_closed():
                    client = None
            except Exception:
                client = None
        else:
            client = None

    if client is None:
        client = MaximoMCPClient()
        run_async(client.connect_to_server())
        st.session_state.mcp_client = client
    return client

# Add CSS for sticky right column and better scrolling
st.markdown("""
    <style>
        /* Main container layout */
        .main > div {
            display: flex;
            gap: 20px;
        }
        
        /* Left column - scrollable chat */
        [data-testid="column"]:nth-of-type(1) {
            flex: 2;
            display: flex;
            flex-direction: column;
            height: 100vh;
            gap: 10px;
        }
        
        /* Chat messages container - scrollable, grows to fill space */
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column-reverse;
            padding-right: 15px;
            padding-bottom: 10px;
        }
        
        /* Input area - stays at bottom */
        .chat-input-area {
            flex-shrink: 0;
            padding: 15px 0;
            border-top: 1px solid #e0e0e0;
            background: white;
            position: sticky;
            bottom: 0;
            z-index: 100;
        }
        
        /* Right column - sticky analysis panel */
        [data-testid="column"]:nth-of-type(2) {
            flex: 1;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            padding-left: 15px;
            background: linear-gradient(135deg, #f0f4ff 0%, #e6f2ff 100%);
            border-left: 3px solid #0066cc;
            border-radius: 10px;
        }
        
        /* Query analysis box styling */
        .query-analysis-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-left: 5px solid #1976d2;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(25, 118, 210, 0.15);
        }
        
        .query-analysis-box h3 {
            color: #0d47a1;
            margin-top: 0;
            font-size: 18px;
        }
        
        /* Expander styling for analysis */
        .stExpander {
            background: rgba(255, 255, 255, 0.9) !important;
            border-left: 4px solid #0066cc !important;
            margin: 8px 0 !important;
        }
        
        /* Custom scrollbars */
        ::-webkit-scrollbar {
            width: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #0066cc;
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #0052a3;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for reasoning tracking
if "query_reasoning" not in st.session_state:
    st.session_state.query_reasoning = None

# Create layout: left for chat, right for reasoning
left_col, right_col = st.columns([2, 1], gap="medium")

with left_col:
    # Chat messages container - scrollable
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
        
        # --- Display Conversation History (reversed for newest at top) ---------------
        messages = st.session_state.get("messages", [])
        for message in reversed(messages):
            with st.chat_message(message["role"], avatar=message.get("avatar")):
                st.markdown(message["content"])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area - fixed at bottom
    st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)
    
    # --- Handle prefilled questions ---------------
    prefill = st.session_state.pop("prefilled_question", None)

    # --- User Input (stays at bottom) ---------------
    user_input = st.chat_input("Ask a question about your Maximo data...")

    # --- use prefilled question if button was clicked ---
    prompt = user_input or prefill
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if prompt:
        # Display user message immediately
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": "👤"})

        # get MCP CLient
        try:
            client = get_mcp_client()
        except Exception as e:
            st.error(f"Error connecting to Maximo MCP Server: {e}")
            st.stop()

        # Process the query with MCP Client
        try:
            print(f"Processing query: {prompt}", file=sys.stderr, flush=True)
            result = run_async(client.process_query(prompt, st.session_state.conversation_history))
            
            # Handle both tuple and string returns for backward compatibility
            if isinstance(result, tuple):
                response, reasoning = result
            else:
                response = result
                reasoning = None
            
            #Update conversation history and messages for display                
            st.session_state.messages.append({"role": "assistant", "content": response, "avatar": "🤖"})
            st.session_state.conversation_history.append({"role": "user", "content": prompt})
            st.session_state.conversation_history.append({"role": "assistant", "content": response})
            st.session_state.query_reasoning = reasoning
            st.rerun()
        except Exception as e:
            trace = traceback.format_exc()
            error_message = f"Error processing query: {e}"
            st.error(error_message)
            st.error("See traceback below:")
            st.code(trace)
            st.session_state.messages.append({"role": "assistant", "content": error_message, "avatar": "🤖"})

with right_col:
    # --- Right Panel: Query Reasoning & Steps ---------------
    st.markdown('<div class="query-analysis-box"><h3>📊 Query Analysis</h3></div>', unsafe_allow_html=True)
    
    if st.session_state.query_reasoning:
        reasoning = st.session_state.query_reasoning
        
        # Display Query with highlighting
        with st.expander("🔍 Query", expanded=True):
            st.info(reasoning.get("query", "N/A"))
        
        # Display Tools Used
        if reasoning.get("tools_used"):
            with st.expander("🛠️ Tools Used", expanded=True):
                for tool in reasoning["tools_used"]:
                    st.write(f"- **{tool['name']}**")
                    if tool.get("args"):
                        st.json(tool["args"])
        
        # Display Reasoning Steps
        if reasoning.get("steps"):
            with st.expander("🧠 Reasoning Steps", expanded=True):
                for i, step in enumerate(reasoning["steps"], 1):
                    st.write(f"**Step {i}:** {step}")
        
        # Display Tool Results
        if reasoning.get("tool_results"):
            with st.expander("📋 Tool Results", expanded=False):
                for result in reasoning["tool_results"]:
                    st.write(f"**{result['tool']}**")
                    st.json(result["result"])
    else:
        st.info("Query analysis will appear here after processing")