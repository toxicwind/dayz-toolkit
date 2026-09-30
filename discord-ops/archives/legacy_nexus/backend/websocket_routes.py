"""
WebSocket endpoint for real-time log streaming.
Integrates with log_streamer module to broadcast server logs to connected clients.
"""

import logging

from fastapi import WebSocket, WebSocketDisconnect

from .log_streamer import get_streamer

log = logging.getLogger("dayz-discord-ops.websocket-routes")


async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live log streaming - Aggressive Permissive Mode"""
    # NOTE: accept() is now called by the parent route handler in api.py
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
