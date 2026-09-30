from enum import Enum

class EventKind(Enum):
    # Log Events
    LOG_INGESTED = "log.ingested"
    LOG_PARSED = "log.parsed"
    
    # Killfeed Events
    KILLFEED_BROADCAST = "killfeed.broadcast"
    KILLFEED_POI_RESOLVED = "killfeed.poi_resolved"
    
    # System Events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_RESTART = "system.restart"
    
    # Command Events
    COMMAND_TRIGGERED = "command.triggered"
    DEMO_MODE_START = "demo.mode.start"
