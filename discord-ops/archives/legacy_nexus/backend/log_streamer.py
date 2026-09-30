"""
Real-time log streaming service for DayZ server.
Aggregates logs from Nitrado WebSocket and FTP and broadcasts to WebSocket clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

import websockets

# NOTE: Using FastAPI WebSocket for client connections, not websockets.WebSocketServerProtocol
from fastapi import WebSocket

from . import metrics
from .adm_log_parser import ADMLogParser
from .analytics import AnalyticsEngine
from .nitrado_api import NitradoAPIClient
from .rpt_parser import RPTLogParser

log = logging.getLogger("dayz-discord-ops.log-streamer")

# Log event types
LogLevel = Literal["info", "warn", "error", "combat", "admin", "system"]
LogSource = Literal["nitrado", "ftp"]


@dataclass
class LogEvent:
    """Structured log event"""

    timestamp: str
    source: LogSource
    level: LogLevel
    message: str
    player: str | None = None
    player_id: str | None = None
    victim: str | None = None
    victim_id: str | None = None
    weapon: str | None = None
    distance: float | None = None
    location: str | None = None
    raw: str | None = None
    correlation_id: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))


Listener = Callable[[LogEvent], Awaitable[None]]


class LogStreamer:
    """Manages real-time log streaming from multiple sources"""

    def __init__(
        self,
        nitrado_token: str | None = None,
        nitrado_service_id: int | None = None,
        ftp_host: str | None = None,
        ftp_port: int = 21,
        ftp_user: str | None = None,
        ftp_pass: str | None = None,
        platform: str = "pc",
    ):
        self.nitrado_token = nitrado_token
        self.nitrado_service_id = nitrado_service_id
        self.platform = platform
        self.ftp_config = {
            "host": ftp_host,
            "port": ftp_port,
            "user": ftp_user,
            "passwd": ftp_pass,
        }

        # Connected WebSocket clients (FastAPI WebSocket type)
        self.clients: set[WebSocket] = set()

        # Log buffer (keep last 1000 events)
        self.log_buffer: deque[LogEvent] = deque(maxlen=1000)

        # Background tasks
        self.tasks: list[asyncio.Task] = []

        # External listeners (e.g., killfeed dispatcher)
        self._listeners: set[Listener] = set()

        # Deduplication
        self.processed_hashes: deque[int] = deque(maxlen=5000)

        # Persistent storage path
        self.log_file_path = "logs/server_logs_persistent.jsonl"
        os.makedirs("logs", exist_ok=True)

        # Parsers
        self.adm_parser = ADMLogParser()
        self.rpt_parser = RPTLogParser()

        # Analytics (needs DB, usually passed or fetched via get_db)
        from .config import get_settings
        from .database import Database

        self.db = Database(get_settings())
        self.analytics = AnalyticsEngine(self.db)

    async def _publish_to_bus(self, event: LogEvent):
        """Bridge high-value log events to the global EventBus."""
        from .events import get_bus

        bus = get_bus()

        # Ensure we have a CID
        cid = event.correlation_id or "legacy-no-cid"

        # Map LogEvent to EventBus topics
        if event.level == "combat" or (event.player and event.victim):
            # Structuring payload for Discord Live Updates
            payload = {
                "timestamp": event.timestamp,
                "killer": event.player,
                "killer_id": event.player_id,
                "victim": event.victim,
                "victim_id": event.victim_id,
                "weapon": event.weapon,
                "distance": event.distance,
                "location": event.location,
                "_correlation_id": cid,
            }
            await bus.publish("killfeed.kill", payload)
        elif event.level == "admin":
            await bus.publish(
                "admin.action",
                {
                    "timestamp": event.timestamp,
                    "type": "Admin Log",
                    "admin": "System/RCON",  # Parsers might need to extract this better later
                    "reason": event.message,
                    "_correlation_id": cid,
                },
            )

    def add_listener(self, listener: Listener) -> None:
        self._listeners.add(listener)

    def remove_listener(self, listener: Listener) -> None:
        self._listeners.discard(listener)

    async def start(self):
        """Start all log streaming sources"""
        log.info(f"Starting log streamer (Platform: {self.platform})...")

        # Start Nitrado service logs API (service events: restarts, uploads)
        if self.nitrado_token and self.nitrado_service_id:
            task = asyncio.create_task(self._poll_nitrado_api_logs())
            self.tasks.append(task)
            log.info("Log streamer started with Nitrado service logs API")

        # Start FTP Log Ingestion (game server logs: ADM/RPT files)
        ftp_task = asyncio.create_task(self._poll_ftp_logs())
        self.tasks.append(ftp_task)
        log.info("Log streamer started with FTP Log Ingestion")

        # Subscribe to EventFabric (Bus -> WS Bridge)
        from .events import get_bus

        bus = get_bus()
        bus.subscribe("killfeed.kill", self._on_bus_event)
        bus.subscribe("admin.action", self._on_bus_event)
        log.info("LogStreamer bridged to EventFabric (Bus -> WS)")

    async def _on_bus_event(self, payload: dict):
        """Handle events from the bus and broadcast to WS clients."""
        # Avoid re-broadcasting if we originated it (simple check or different topics?)
        # For now, we trust the 'source' or just broadcast.
        # LogStreamer.broadcast accepts LogEvent or JSON?
        # _broadcast_event takes LogEvent.
        # We need to convert payload back to LogEvent or just send raw JSON.
        # Let's send raw JSON to clients for maximum flexibility.
        if self.clients:
            message = json.dumps(payload)
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send_text(message)
                except Exception as e:
                    log.error(f"Failed to send bus event to client: {e}")
                    disconnected.add(client)
            self.clients -= disconnected

    async def stop(self):
        """Stop all streaming tasks"""
        log.info("Stopping log streamer...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        log.info("Log streamer stopped")

    async def _stream_nitrado_logs(self):
        # Skip if WebSocket disabled (endpoint undocumented, returns 404)
        if os.getenv("NITRADO_WS_DISABLED", "true").lower() == "true":
            log.info("Nitrado WebSocket disabled (NITRADO_WS_DISABLED=true), using FTP polling only")
            return

        """Stream logs from Nitrado WebSocket"""
        log.info("Starting Nitrado WebSocket stream...")

        # Get WebSocket token
        client = NitradoAPIClient(self.nitrado_token)
        ws_token = client.get_websocket_token(self.nitrado_service_id)

        if not ws_token:
            log.error("Failed to get Nitrado WebSocket token")
            return

        # Nitrado WebSocket URL (this is a placeholder - need to verify actual endpoint)
        # Based on the API docs, the websocket_token is provided but the endpoint isn't documented
        # We may need to use wss://api.nitrado.net/services/{service_id}/gameservers/console
        ws_url = f"wss://api.nitrado.net/services/{self.nitrado_service_id}/gameservers/console?token={ws_token}"

        retry_delay = 1
        max_retry_delay = 60

        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    self.nitrado_ws = ws
                    log.info("Connected to Nitrado WebSocket")
                    retry_delay = 1  # Reset retry delay on successful connection

                    async for message in ws:
                        event = self._parse_nitrado_message(message)
                        if event:
                            await self._broadcast_event(event)

            except Exception as e:
                log.error(f"Nitrado WebSocket error: {e}")
                self.nitrado_ws = None

                # Exponential backoff
                log.info(f"Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _poll_ftp_logs(self):
        """Poll FTP logs using robust FTPLogIngestor"""
        log.info("Starting FTP log ingestion (Robust Mode)...")
        from .ftp_ingestor import FTPLogIngestor

        # In this standalone context, we let Ingestor use its fallback load_settings()
        # or we could pass one.
        ingestor = FTPLogIngestor()
        poll_interval = 2  # Reduced from 10s for real-time feel

        while True:
            try:
                # Now async-capable, call directly
                events = await ingestor.process()

                if events:
                    log.info(f"FTP Ingestor found {len(events)} new events")
                    for event in events:
                        await self._broadcast_event(event)

                await asyncio.sleep(poll_interval)
            except Exception as e:
                log.error(f"FTP ingestion error: {e}")
                await asyncio.sleep(poll_interval)

    async def _poll_nitrado_api_logs(self):
        """Poll Nitrado service logs API for server events"""
        log.info("Starting Nitrado service logs polling...")
        client = NitradoAPIClient(self.nitrado_token)
        poll_interval = 5  # Reduced from 30s

        # Load cursor from file
        cursor_path = Path("logs/nitrado_cursor.txt")
        last_seen_timestamp = None
        if cursor_path.exists():
            try:
                last_seen_timestamp = cursor_path.read_text().strip()
                log.info(f"Loaded Nitrado log cursor: {last_seen_timestamp}")
            except Exception as e:
                log.error(f"Failed to read cursor file: {e}")

        while True:
            try:
                # Get service logs (restarts, status changes, etc)
                # FIXED: client.get_service_logs is already async
                logs_data = await client.get_service_logs(self.nitrado_service_id, page=1)

                # Heartbeat for supervisor monitor
                from .supervisor import get_supervisor

                supervisor = await get_supervisor()
                supervisor.heartbeat("nitrado_api_polling")

                if not logs_data or "logs" not in logs_data:
                    await asyncio.sleep(poll_interval)
                    continue

                # Nitrado logs are usually newest first
                # We process them in reverse order (oldest -> newest) to preserve timeline
                # BUT we need to filter safely.

                new_logs = []
                current_batch_max_ts = last_seen_timestamp

                for log_entry in reversed(logs_data["logs"]):
                    timestamp = log_entry.get("created_at")

                    # Skip if we've seen this before (or it's older)
                    if last_seen_timestamp and timestamp <= last_seen_timestamp:
                        continue

                    new_logs.append(log_entry)
                    current_batch_max_ts = timestamp

                # Process new logs
                for log_entry in new_logs:
                    timestamp = log_entry.get("created_at")
                    event = LogEvent(
                        level=log_entry.get("severity", "info"),
                        message=f"[{log_entry.get('category')}] {log_entry.get('message')}",
                        source="nitrado_service",
                        timestamp=timestamp,
                        raw=f"{timestamp} [{log_entry.get('category')}] {log_entry.get('message')}",
                    )
                    await self._broadcast_event(event)

                # Update cursor if we processed anything
                if current_batch_max_ts != last_seen_timestamp:
                    last_seen_timestamp = current_batch_max_ts
                    try:
                        cursor_path.write_text(str(last_seen_timestamp))
                    except Exception as e:
                        log.error(f"Failed to save cursor: {e}")

                await asyncio.sleep(poll_interval)

            except Exception as e:
                log.error(f"Nitrado service logs polling error: {e}")
                await asyncio.sleep(poll_interval)

    def _parse_generic_log_line(self, line: str, source: str, log_type: str) -> LogEvent | None:
        """Generic parser for various log lines using advanced RPT/ADM parsers"""
        try:
            level: LogLevel = "info"
            player = None
            player_id = None
            victim_id = None

            # Determine which parser to use
            if log_type == "adm":
                event = self.adm_parser.parse_line(line)
                if event:
                    player = event.player_name
                    # Extract IDs from event data if available
                    player_id = event.player_id or event.data.get("attacker_id")
                    victim_id = event.data.get("victim_id")

                    if event.event_type in ["kill", "hit"]:
                        level = "combat"
                    elif event.event_type == "building":
                        level = "admin"  # Or "info"
                    elif event.event_type == "suicide":
                        level = "combat"
            elif log_type == "rpt":
                event = self.rpt_parser.parse_line(line)
                if event:
                    # Update metrics based on RPT events
                    if event.event_type == "fps":
                        metrics.SERVER_FPS.set(float(event.data["fps"]))
                    elif event.event_type == "memory":
                        metrics.MEMORY_VIRT.set(float(event.data["virt"]))
                        metrics.MEMORY_PHYS.set(float(event.data["phys"]))
                    elif event.event_type == "search_overtime":
                        metrics.SEARCH_OVERTIME.labels(item=event.data["item_name"]).inc()
                    elif event.event_type == "hard_to_place":
                        metrics.HARD_TO_PLACE.labels(item=event.data["item_name"]).inc()
                    elif event.event_type == "script_error":
                        metrics.SCRIPT_ERRORS.labels(level=event.data["level"]).inc()
                        level = "error" if event.data["level"] == "Error" else "warn"

                    if event.event_type in ["player_connect", "player_disconnect"]:
                        player = event.data["name"]
                        player_id = event.data.get("id")

            # Fallback for classification if no event matched
            if level == "info":
                line_lower = line.lower()
                if "error" in line_lower or "exception" in line_lower:
                    level = "error"
                elif "warn" in line_lower:
                    level = "warn"
                elif "admin" in line_lower or "kick" in line_lower or "ban" in line_lower:
                    level = "admin"

            return LogEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="nitrado" if "nitrado" in source else "ftp",
                level=level,
                message=line.strip(),
                player=player,
                player_id=player_id,
                victim_id=victim_id,
                raw=line,
                correlation_id=str(uuid.uuid4()),
            )
        except Exception as e:
            log.error(f"Generic parse error: {e}")
            return None

    def _parse_nitrado_message(self, message: str) -> LogEvent | None:
        """Parse Nitrado WebSocket message into LogEvent"""
        try:
            level: LogLevel = "info"
            player = None
            player_id = None
            victim = None
            victim_id = None
            weapon = None
            distance = None
            location = None

            msg_lower = message.lower()

            # High-priority check: Use ADM parser patterns (they are more robust)
            adm_event = self.adm_parser.parse_line(message)
            if adm_event:
                level = "info"
                if adm_event.event_type in ["kill", "suicide"]:
                    level = "combat"
                elif adm_event.event_type == "hit":
                    level = "combat"

                return LogEvent(
                    timestamp=adm_event.timestamp.isoformat(),
                    source="nitrado",
                    level=level,
                    message=message.strip(),
                    player=adm_event.player_name,
                    player_id=adm_event.player_id,
                    victim=adm_event.data.get("victim_name"),
                    victim_id=adm_event.data.get("victim_id"),
                    weapon=adm_event.data.get("weapon"),
                    distance=float(adm_event.data.get("dist", 0)) if adm_event.data.get("dist") else None,
                    raw=message,
                    correlation_id=str(uuid.uuid4()),
                )

            # Fallback to old regex/killfeed parser

            if parsed_kill:
                level = "combat"
                player = parsed_kill.killer
                victim = parsed_kill.victim
                # killfeed parser might not extract IDs yet, try regex if missing
                weapon = parsed_kill.weapon
                distance = parsed_kill.distance_m
                location = parsed_kill.location
            # Fallback categorization
            elif "error" in msg_lower or "exception" in msg_lower:
                level = "error"
            elif "warn" in msg_lower or "warning" in msg_lower:
                level = "warn"
            elif "admin" in msg_lower or "ban" in msg_lower or "kick" in msg_lower:
                level = "admin"

            # Always try to extract IDs using regex
            # Patterns:
            # Player "Survivor" (id=123456789)
            # Player 'Survivor' (id=123456789)
            import re

            # Simple player extraction if not set
            if not player and "player" in msg_lower:
                match = re.search(r"player[:\s]+['\"]?([^'\"\s]+)['\"]?", message, re.IGNORECASE)
                if match:
                    player = match.group(1)

            # ID Extraction (Console ID patterns generally look like id=...)
            # Find all (name, id) pairs
            id_matches = re.findall(r"['\"]([^'\"]+)['\"]\s*\(id=([^\)]+)\)", message)

            if id_matches:
                # If we have a player name, try to match it to an ID
                if player:
                    for name, pid in id_matches:
                        if name == player:
                            player_id = pid
                            break
                    # If not found but only one match, assume it's the player
                    if not player_id and len(id_matches) == 1:
                        player_id = id_matches[0][1]

                # If we have a victim name, try to match it
                if victim:
                    for name, pid in id_matches:
                        if name == victim:
                            victim_id = pid
                            break

            return LogEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="nitrado",
                level=level,
                message=message.strip(),
                player=player,
                player_id=player_id,
                victim=victim,
                victim_id=victim_id,
                weapon=weapon,
                distance=distance,
                location=location,
                raw=message,
            )
        except Exception as e:
            log.error(f"Failed to parse Nitrado message: {e}")
            return None

    def _parse_ftp_log_line(self, line: str, filename: str) -> LogEvent | None:
        """Parse FTP log line into LogEvent"""
        try:
            from .killfeed import parse_kill_event

            level: LogLevel = "info"
            player = None
            victim = None
            weapon = None
            distance = None
            location = None

            # Try killfeed parser first
            parsed_kill = parse_kill_event(line)
            if parsed_kill:
                level = "combat"
                player = parsed_kill.killer
                victim = parsed_kill.victim
                weapon = parsed_kill.weapon
                distance = parsed_kill.distance_m
                location = parsed_kill.location
            else:
                if "admin" in line.lower():
                    level = "admin"

                # ADM logs have format: timestamp | player | action | details
                if "ADM_Log" in filename:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        player = parts[1].strip()
                        import re

                        loc_match = re.search(r"\[(\d+),\s*(\d+)\]", line)
                        if loc_match:
                            location = f"{loc_match.group(1)},{loc_match.group(2)}"

            return LogEvent(
                timestamp=datetime.utcnow().isoformat(),
                source="ftp",
                level=level,
                message=line.strip(),
                player=player,
                victim=victim,
                weapon=weapon,
                distance=distance,
                location=location,
                raw=line,
            )
        except Exception as e:
            log.error(f"Failed to parse FTP log line: {e}")
            return None

    async def _broadcast_event(self, event: LogEvent):
        """Broadcast log event to all connected clients and store persistently"""
        # Deduplication check (extra safety)
        msg_hash = hash(event.message)
        if msg_hash in self.processed_hashes and event.source != "nitrado":
            # Allow nitrado ws messages through as they are real-time,
            # but others might be duplicates from polling
            return

        self.processed_hashes.append(msg_hash)

        # Perform deep analytics/logging
        # Determine org_id (log streamer is currently global, might need tenant-specific logic later)
        # For now, we use a default if not detectable or let analytics handle it
        org_id = "global"  # TODO: Map event to org_id based on service_id/source

        # Re-parse for analytics objects if needed or pass the raw line
        if event.raw and (".ADM" in event.raw.upper() or event.level == "combat"):
            parsed_adm = self.adm_parser.parse_line(event.raw)
            if parsed_adm:
                self.analytics.process_event(org_id, parsed_adm)
        elif event.raw and (".RPT" in event.raw.upper() or event.level in ["error", "warn"]):
            parsed_rpt = self.rpt_parser.parse_line(event.raw)
            if parsed_rpt:
                self.analytics.process_event(org_id, parsed_rpt)

        # Add to buffer
        self.log_buffer.append(event)

        # Persistent storage (append_persistent_log is sync, so to_thread is correct here)
        try:
            await asyncio.to_thread(self._append_persistent_log, event.to_json())
        except Exception as e:
            log.error(f"Failed to write to persistent log: {e}")

        # Broadcast to all clients
        if self.clients:
            message = event.to_json()
            disconnected = set()

            for client in self.clients:
                try:
                    await client.send_text(message)
                except Exception as e:
                    log.error(f"Failed to send to client: {e}")
                    disconnected.add(client)

            # Remove disconnected clients
            self.clients -= disconnected

        # Bridge to Event Fabric
        await self._publish_to_bus(event)

        if self._listeners:
            await self._notify_listeners(event)

    def _append_persistent_log(self, line: str) -> None:
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def _notify_listeners(self, event: LogEvent) -> None:
        coros = []
        for listener in list(self._listeners):
            try:
                coros.append(listener(event))
            except Exception:
                log.exception("Failed to schedule log listener")
        if not coros:
            return
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.error("Log listener raised error: %s", result)

    async def handle_client(self, websocket: WebSocket):
        """Handle a WebSocket client connection (FastAPI WebSocket)"""
        log.info(f"New log client connected: {websocket.client}")
        self.clients.add(websocket)

        try:
            # Send buffered logs to new client
            for event in self.log_buffer:
                await websocket.send_text(event.to_json())

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    message = await websocket.receive_text()
                    # Clients can send filter preferences, etc.
                    data = json.loads(message)
                    log.debug(f"Client message: {data}")
                except json.JSONDecodeError:
                    log.warning(f"Invalid JSON from client: {message}")
                except Exception as e:
                    log.debug(f"Client message handling error: {e}")
                    break

        except Exception as e:
            log.info(f"Log client disconnected: {websocket.client} ({e})")
        finally:
            self.clients.discard(websocket)


# Global streamer instance
_streamer: LogStreamer | None = None


def get_streamer() -> LogStreamer:
    """Get or create the global log streamer instance"""
    global _streamer
    if _streamer is None:
        # Initialize from settings
        from .config import load_settings

        s = load_settings()
        _streamer = LogStreamer(
            nitrado_token=s.nitrado_token,
            nitrado_service_id=s.nitrado_service_id,
            ftp_host=s.ftp_host,
            ftp_port=s.ftp_port,
            ftp_user=s.ftp_user,
            ftp_pass=s.ftp_password,
            platform=s.platform,
        )
    return _streamer
