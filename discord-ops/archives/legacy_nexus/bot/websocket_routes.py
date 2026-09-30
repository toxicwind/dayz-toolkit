"""
WebSocket endpoint for real-time log streaming.
Integrates with log_streamer module to broadcast server logs to connected clients.
"""
from fastapi import WebSocket, WebSocketDisconnect
from .log_streamer import get_streamer
import logging

log = logging.getLogger("dayz-discord-ops.websocket-routes")


async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live log streaming - Aggressive Permissive Mode"""
    # unconditional accept for internal/dev usage
    await websocket.accept()
    
    streamer = get_streamer()
    
    # Start streamer if not already running
    if not streamer.tasks:
        await streamer.start()
    
    try:
        await streamer.handle_client(websocket)
    except WebSocketDisconnect:
        log.info("Client disconnected from log stream")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
