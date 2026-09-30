import logging
from typing import Any
from .parser import KillfeedParser
from .types import CombatEvent
from src.mildlyawesome.core.bus import bus

log = logging.getLogger("mildlyawesome.killfeed")

class KillfeedEngine:
    def __init__(self, settings):
        self.settings = settings
        self.parser = KillfeedParser()
        
    async def initialize(self):
        """Subscribe to the event bus for log ingestion."""
        bus.subscribe("log.ingested", self.on_log_ingested)
        log.info("⚔️ Killfeed Engine Initialized & Subscribed to LogStream")

    async def on_log_ingested(self, log_event: Any):
        """Unified hook for all log ingestion (RCON, FTP, Selfplay)."""
        # log_event is expected to have timestamp and message
        # level check
        if hasattr(log_event, "level") and log_event.level != "combat" and "DEAD" not in log_event.message:
            return

        combat_event = self.parser.parse_line(log_event.timestamp, log_event.message)
        if combat_event:
            log.info(f"⚔️ Killfeed: {combat_event.killer_name} PK'd {combat_event.victim_name}")
            await bus.publish("killfeed.broadcast", combat_event)
            return combat_event
        return None
