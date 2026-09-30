"""
MCP (Model Context Protocol) Endpoint for DayZ Discord Ops Backend.

This module exposes the DayZ Backend's API operations as MCP tools,
allowing the Agent Gateway to route requests to this src.mildlyawesome.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from .fleet import get_registry

log = logging.getLogger(__name__)

router = APIRouter()

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class MCPToolsListResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Dict[str, Any]

class MCPToolCallRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

# Define tools that map to our API endpoints
TOOLS = [
    {
        "name": "dayz_fleet_list",
        "description": "Lists all available DayZ server fleets (tenants) managed by this system.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "dayz_economy_item_lookup",
        "description": "Looks up an item's economy stats (nominal, min, restock, lifetime) from the types.xml for a specific fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The fleet/service ID (e.g., 'ezstreet')"},
                "item_name": {"type": "string", "description": "The exact item classname to lookup"}
            },
            "required": ["service_id", "item_name"]
        }
    },
    {
        "name": "dayz_fleet_status",
        "description": "Gets the current status of a specific DayZ fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The fleet/service ID"}
            },
            "required": ["service_id"]
        }
    },
    {
        "name": "dayz_server_restart",
        "description": "Restarts a specific DayZ server fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The fleet/service ID"},
                "message": {"type": "string", "description": "Optional restart message"}
            },
            "required": ["service_id"]
        }
    },
    {
        "name": "dayz_player_ban",
        "description": "Bans a player from the server fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The fleet/service ID"},
                "gamertag": {"type": "string", "description": "The player's gamertag"}
            },
            "required": ["service_id", "gamertag"]
        }
    },
    {
        "name": "chronos_exhume",
        "description": "Triggers autonomous exhumation of configuration keys and system ghosts.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "chronos_query",
        "description": "Performs an emergent multi-vector query across local and external ecosystems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query string to search for"},
                "emergent_mode": {"type": "boolean", "description": "Whether to use emergent context retrieval"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "chronos_entropy",
        "description": "Returns a heatmap of system instability and file entropy.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

@router.post("/mcp")
@router.post("/mcp/")
async def mcp_handler(request: Request):
    """
    JSON-RPC 2.0 handler for MCP protocol.
    """
    try:
        body = await request.json()
    except:
        return {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
    
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")
    
    log.info(f"MCP Request: method={method}, id={req_id}")
    
    # Handle standard MCP methods
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS,
                "nextCursor": None  # Explicitly null for tool-mesh compliance
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        result = await execute_tool(tool_name, tool_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

async def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with the given arguments."""
    
    if name == "dayz_fleet_list":
        registry = get_registry()
        services = registry.list_services()
        return {
            "content": [
                {"type": "text", "text": str([{"id": s.id, "name": s.name, "platform": s.platform} for s in services])}
            ]
        }
    
    elif name == "dayz_fleet_status":
        service_id = args.get("service_id")
        registry = get_registry()
        settings = registry.get_service(service_id)
        if not settings:
            return {"content": [{"type": "text", "text": f"Service '{service_id}' not found."}]}
        return {
            "content": [
                {"type": "text", "text": f"Fleet: {settings.server_name}, Platform: {settings.platform}"}
            ]
        }
    
    elif name == "dayz_economy_item_lookup":
        from modules.types_editor.service import TypesService
        from modules.types_editor.api import get_registry
        
        service_id = args.get("service_id")
        item_name = args.get("item_name")
        
        registry = get_registry()
        settings = registry.get_service(service_id)
        if not settings:
             return {"content": [{"type": "text", "text": f"Service '{service_id}' not found."}]}
             
        mission_path = settings.mission_path
        if not mission_path:
             # Fallback to configured staging path if it exists
             staging_mission = get_registry().get_service(service_id).mission_path
             if staging_mission:
                 mission_path = staging_mission
             elif service_id == "ezstreet":
                 from .config import get_settings
                 mission_path = str(get_settings().staging_dir / "dayzxb_missions/dayzOffline.chernarusplus")
             
        if not mission_path:
             return {"content": [{"type": "text", "text": f"Mission path not configured for '{service_id}'."}]}

        path = TypesService.get_types_path(mission_path)
        try:
            data = TypesService.parse_xml(path)
            # Find the item
            item = next((i for i in data.types if i.name == item_name), None)
            if not item:
                 return {"content": [{"type": "text", "text": f"Item '{item_name}' not found in types.xml for '{service_id}'."}]}
            
            stats = f"Item: {item.name}\nNominal: {item.nominal}\nMin: {item.min}\nRestock: {item.restock}\nLifetime: {item.lifetime}"
            return {
                "content": [
                    {"type": "text", "text": stats}
                ]
            }
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error parsing types.xml: {e}"}]}
    
    elif name == "dayz_server_restart":
        from .nitrado_sdk_client import create_client_from_config
        service_id = args.get("service_id")
        message = args.get("message", "Restarting via MCP Tool")
        try:
            client = create_client_from_config(service_id)
            res = await client.restart_server(message)
            return {"content": [{"type": "text", "text": f"Restart triggered: {res}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}

    elif name == "dayz_player_ban":
        from .nitrado_sdk_client import create_client_from_config
        service_id = args.get("service_id")
        gamertag = args.get("gamertag")
        try:
            client = create_client_from_config(service_id)
            res = await client.ban_player(gamertag)
            return {"content": [{"type": "text", "text": f"Ban result: {res}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}

    elif name == "chronos_exhume":
        from modules.chronos.service import ChronosService
        try:
            res = await ChronosService.run_chronos_audit()
            return {"content": [{"type": "text", "text": f"Exhumation complete: {res}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}

    elif name == "chronos_query":
        from modules.chronos.service import ChronosService
        query = args.get("query")
        emergent = args.get("emergent_mode", True)
        try:
            res = await ChronosService.predator_query(query, emergent)
            # Use json.dumps for structured output
            import json
            return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}

    elif name == "chronos_entropy":
        from modules.chronos.service import ChronosService
        try:
            res = await ChronosService.entropy_scan()
            import json
            return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}

    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
