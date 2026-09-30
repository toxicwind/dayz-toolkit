from fastapi import APIRouter
import logging

log = logging.getLogger("mildlyawesome.api.mcp")
router = APIRouter()

@router.get("/")
async def mcp_index():
    return {"status": "ok", "message": "MildlyAwesome MCP Gateway"}

@router.post("/rpc")
async def mcp_rpc():
    return {"jsonrpc": "2.0", "result": "stub", "id": 1}
