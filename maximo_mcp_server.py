import json
import sys
from mcp.server.fastmcp import FastMCP
from maximo_client import MaximoClient
import maximo_client

# Initialize FastMCP Server
mcp = FastMCP("Maximo Q&A Server")

# Initialize Maximo Client
maximo = MaximoClient()

@mcp.tool()
def search_work_orders(status: str = None, site_id: str = None, max_items: int = 10) -> str:
    """Fetch Work Orders from Maximo."""
    print(f"Received search_work_orders call with status: {status}, site_id: {site_id}, max_items: {max_items}", file=sys.stderr, flush=True)
    
    where_clauses = []
    if status:
        where_clauses.append(f"status=\"{status.replace("'", "\\'")}\"")
    if site_id:
        where_clauses.append(f"siteid=\"{site_id.replace("'", "\\'").replace(' ', '')}\"")
    where_clause = " AND ".join(where_clauses) if where_clauses else None
    select = "wonum, description,status,statusdate, type, siteid, reportedby, assetnum, location"
    try:
        print(f"Fetching work orders with where_clause: {where_clause}, select: {select}, max_items: {max_items}", file=sys.stderr, flush=True)
        results = maximo.get_work_orders(where_clause=where_clause, select=select, max_items=max_items)
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        print(f"Error fetching work orders: {e}", file=sys.stderr, flush=True)
        return json.dumps({"error": str(e)})
    
@mcp.tool()
def find_maximo_object_details(whereclause: str = None, max_items: int = 1, object_name: str = None) -> str:
    """Fetch Object Details from Maximo."""
    print(f"Received find_maximo_object_details call with whereclause: {whereclause}, max_items: {max_items}, object_name: {object_name}", file=sys.stderr, flush=True)

    where_clauses = []
    if whereclause:
        where_clauses.append(f"{whereclause.replace("'", "\"").replace(' ', '')}")
    
    where_clause = " 1=1 and ".join(where_clauses) if where_clauses else None
    select = "*"
    try:
        print(f"Fetching object details with where_clause: {where_clause}, select: {select}, max_items: {max_items}, object_name: {object_name}", file=sys.stderr, flush=True)
        results = maximo.get_object_details(where_clause=where_clause, select=select, max_items=max_items, object_name=object_name)
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        print(f"Error fetching object details: {e}", file=sys.stderr, flush=True)
        return json.dumps({"error": str(e)})
    


@mcp.tool()
def search_non_work_order_objects(whereclause: str = None, max_items: int = 10, object_name: str = None) -> str:
    """Fetch Non-Work Order Objects from Maximo."""
    print(f"Received search_non_work_order_objects call with whereclause: {whereclause}, max_items: {max_items}, object_name: {object_name}", file=sys.stderr, flush=True)

    where_clauses = []
    if whereclause:
        where_clauses.append(f"{whereclause.replace("'", "\"").replace(' ', '')}")

    where_clause = "1=1 AND ".join(where_clauses) if where_clauses else None
    select = "*"

    if object_name is not None:
        if object_name.lower() == "asset":
            select = "assetnum, description,status,statusdate, type, siteid, location"
        elif object_name.lower() == "location":
            select = "location, description, siteid, status"
        elif object_name.lower() == "sr":
            select = "srnum, description, status, statusdate, type, siteid, reportedby, assetnum, location"

    try:
        print(f"Fetching non-work order objects with where_clause: {where_clause}, select: {select}, max_items: {max_items}", file=sys.stderr, flush=True)
        results = maximo.search_non_work_orders_objects(where_clause=where_clause, select=select, max_items=max_items)
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        print(f"Error fetching non-work order objects: {e}", file=sys.stderr, flush=True)
        return json.dumps({"error": str(e)})
    

# Run the MCP server
if __name__ == "__main__":
    mcp.run(transport="stdio")