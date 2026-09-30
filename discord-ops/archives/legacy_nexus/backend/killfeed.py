from __future__ import annotations

import asyncio
import io
import logging
import re
from collections import deque
from dataclasses import dataclass
from enum import Enum

import discord

from .database import Database
from .log_streamer import LogEvent, get_streamer
from .poi_manager import get_poi_manager

log = logging.getLogger("dayz-discord-ops.combat")


# ============================================================================
# EVENT TYPE ENUM
# ============================================================================


class CombatEventType(Enum):
    """Classification of all combat/death event types"""

    PVP_KILL = "pvp_kill"
    PVP_HIT = "pvp_hit"
    HEADSHOT_KILL = "headshot_kill"
    MELEE_KILL = "melee_kill"
    EXPLOSION_DEATH = "explosion_death"
    VEHICLE_DEATH = "vehicle_death"
    FALL_DEATH = "fall_death"
    BLEED_DEATH = "bleed_death"
    SUICIDE = "suicide"
    ZOMBIE_DEATH = "zombie_death"
    ANIMAL_DEATH = "animal_death"
    DISCONNECT_DEATH = "disconnect_death"
    PVE_DEATH = "pve_death"
    UNKNOWN = "unknown"


# ============================================================================
# ADVANCED REGEX PATTERNS
# ============================================================================

# PVP Hit Pattern (non-lethal damage)
# Example: Player "Victim" (id=ABC pos=<1,2,3>)[HP: 50.0] hit by Player "Killer" (id=DEF pos=<4,5,6>) into Torso for 10.0 damage (Bullet_X) with Weapon from 50.0 meters
PVP_HIT_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"\[HP:\s*(?P<victim_hp>[\d.]+)\]\s*"
    r'hit by Player\s+"(?P<killer>[^"]+)"\s*'
    r"\(id=(?P<killer_id>\S+)\s+pos=<(?P<killer_pos>[^>]+)>\)\s*"
    r"into\s+(?P<hit_location>\S+)\s+"
    r"for\s+(?P<damage>[\d.]+)\s+damage\s*"
    r"(?:\((?P<ammo_type>[^)]+)\))?\s*"
    r"with\s+(?P<weapon>.+?)\s+"
    r"(?:from\s+(?P<distance>[\d.]+)\s+meters|$)",
    re.IGNORECASE,
)

# PVP Kill with Distance Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) killed by Player "Killer" (id=DEF pos=<4,5,6>) with Weapon from 100.5 meters
PVP_KILL_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r'killed by Player\s+"(?P<killer>[^"]+)"\s*'
    r"\(id=(?P<killer_id>\S+)\s+pos=<(?P<killer_pos>[^>]+)>\)\s*"
    r"with\s+(?P<weapon>\S+)\s+"
    r"from\s+(?P<distance>[\d.]+)\s+meters",
    re.IGNORECASE,
)

# Headshot Kill Pattern (hit into Head/Brain with DEAD)
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>)[HP: 0.00] hit by Player "Killer" into Head for 125.0 damage (Bullet_X) with Weapon from 200 meters
HEADSHOT_KILL_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"(?:\[HP:\s*(?P<victim_hp>[\d.]+)\]\s*)?"
    r'hit by Player\s+"(?P<killer>[^"]+)"\s*'
    r"(?:\(id=(?P<killer_id>\S+)\s+pos=<(?P<killer_pos>[^>]+)>\)\s*)?"
    r"into\s+(?P<hit_location>Head|Brain)\s+"
    r"for\s+(?P<damage>[\d.]+)\s+damage\s*"
    r"(?:\((?P<ammo_type>[^)]+)\))?\s*"
    r"with\s+(?P<weapon>.+?)\s+"
    r"(?:from\s+(?P<distance>[\d.]+)\s+meters|$)",
    re.IGNORECASE,
)

# Melee Kill Pattern (no distance specified, or with Melee/Fist weapons)
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>)[HP: 0.00] hit by Player "Killer" into Torso for 75.0 damage with Fists
MELEE_KILL_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"(?:\[HP:\s*(?P<victim_hp>[\d.]+)\]\s*)?"
    r'hit by Player\s+"(?P<killer>[^"]+)"\s*'
    r"(?:\(id=(?P<killer_id>\S+)\s+pos=<(?P<killer_pos>[^>]+)>\)\s*)?"
    r"into\s+(?P<hit_location>\S+)\s+"
    r"for\s+(?P<damage>[\d.]+)\s+damage\s*"
    r"(?:\((?P<ammo_type>[^)]+)\))?\s*"
    r"with\s+(?P<weapon>(?:Fists|Melee\w+|.*Knife|.*Axe|.*Bat|.*Pipe))",
    re.IGNORECASE,
)

# Explosion Death Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) killed by explosion (Grenade_RGD5)
EXPLOSION_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"killed by\s+explosion\s*"
    r"(?:\((?P<explosive>[^)]+)\))?",
    re.IGNORECASE,
)

# Vehicle Death Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>)[HP: 0.00] hit by Offroad_02 with TransportHit
VEHICLE_DEATH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"(?:\[HP:\s*(?P<victim_hp>[\d.]+)\]\s*)?"
    r"hit by\s+(?P<vehicle>\S+)\s+with\s+TransportHit",
    re.IGNORECASE,
)

# Fall Death Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) died from falling
FALL_DEATH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"died from falling",
    re.IGNORECASE,
)

# Bleed Death Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) died. Stats> Water: 45.2 Energy: 12.8 Bleed sources: 3
BLEED_DEATH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"died\.\s*Stats>\s*Water:\s*(?P<water>[\d.]+)\s*Energy:\s*(?P<energy>[\d.]+)\s*Bleed sources:\s*(?P<bleed_count>\d+)",
    re.IGNORECASE,
)

# Suicide Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) committed suicide
SUICIDE_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"(?:committed suicide|smacked themselves)",
    re.IGNORECASE,
)

# Disconnect/Rage Quit Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) pulled the plug
DISCONNECT_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"pulled the plug",
    re.IGNORECASE,
)

# Zombie Death Pattern
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) killed by ZmbM_PatrolNormal_Summer
ZOMBIE_DEATH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"(?:killed by|was last seen eating human flesh).*?(?P<zombie_type>Zmb\w+)?",
    re.IGNORECASE,
)

# Animal Death Pattern (must be checked BEFORE zombie pattern)
# Example: Player "Victim" (DEAD) (id=ABC pos=<1,2,3>) killed by Animal_UrsusArctos
ANIMAL_DEATH_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})?\s*\|?\s*"
    r'Player\s+"(?P<victim>[^"]+)"\s*\(DEAD\)\s*'
    r"\(id=(?P<victim_id>\S+)\s+pos=<(?P<victim_pos>[^>]+)>\)\s*"
    r"killed by\s+Animal_(?P<animal_type>\w+)",
    re.IGNORECASE,
)

# Position extraction pattern (for any line with pos=<x,y,z>)
POSITION_PATTERN = re.compile(r"pos=<(?P<x>[\d.]+),\s*(?P<y>[\d.]+),\s*(?P<z>[\d.]+)>")


# ============================================================================
# ENHANCED DATA CLASSES
# ============================================================================


@dataclass
class ParsedCombatEvent:
    """Enhanced combat event with comprehensive data extraction"""

    event_type: CombatEventType
    timestamp: str

    # Victim information
    victim_name: str
    victim_id: str | None = None
    victim_hp: float | None = None

    # Killer information (None for PVE deaths)
    killer_name: str | None = None
    killer_id: str | None = None

    # Combat details
    weapon: str | None = None
    ammo_type: str | None = None
    distance_m: float | None = None
    hit_location: str | None = None
    damage_dealt: float | None = None

    # Location data
    location_x: float | None = None
    location_y: float | None = None
    location_z: float | None = None

    # Additional metadata
    explosive_type: str | None = None  # For explosion deaths
    vehicle_type: str | None = None  # For vehicle deaths
    animal_type: str | None = None  # For animal deaths
    bleed_count: int | None = None  # For bleed deaths

    # Analytics fields (to be populated by analytics engine)
    streak_count: int = 0
    combat_rating_delta: int = 0

    # Raw log message
    raw_message: str = ""

    def is_pvp(self) -> bool:
        """Check if this is a PVP event"""
        return self.event_type in (
            CombatEventType.PVP_KILL,
            CombatEventType.PVP_HIT,
            CombatEventType.HEADSHOT_KILL,
            CombatEventType.MELEE_KILL,
        )

    def is_kill(self) -> bool:
        """Check if this event resulted in a death"""
        return self.event_type != CombatEventType.PVP_HIT

    def is_headshot(self) -> bool:
        """Check if this was a headshot"""
        return self.event_type == CombatEventType.HEADSHOT_KILL or (
            self.hit_location and self.hit_location.lower() in ("head", "brain")
        )


# ============================================================================
# PARSING FUNCTIONS
# ============================================================================


def _extract_timestamp(message: str) -> str:
    """Extract timestamp from log message"""
    match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", message)
    if match:
        return match.group(1)
    match = re.search(r"(\d{2}:\d{2}:\d{2})", message)
    if match:
        return match.group(1)
    return ""


def _extract_position(pos_string: str) -> tuple[float | None, float | None, float | None]:
    """Extract x, y, z coordinates from position string like '1234.5,6789.0,12.3'"""
    try:
        parts = pos_string.split(",")
        if len(parts) >= 3:
            return float(parts[0].strip()), float(parts[1].strip()), float(parts[2].strip())
    except (ValueError, IndexError):
        pass
    return None, None, None


def parse_combat_event(message: str) -> ParsedCombatEvent | None:
    """
    Parse a combat log message into a structured event.

    Attempts to match against all known patterns in priority order:
    1. PVP Hit (non-lethal)
    2. Headshot Kill
    3. Melee Kill
    4. PVP Kill
    5. Explosion Death
    6. Vehicle Death
    7. Fall Death
    8. Bleed Death
    9. Suicide
    10. Disconnect/Rage Quit
    11. Zombie Death
    12. Animal Death

    Returns ParsedCombatEvent or None if message doesn't match any pattern.
    """
    raw = message.strip()
    if not raw:
        return None

    timestamp = _extract_timestamp(raw)

    # Priority 1: PVP Hit (non-lethal damage)
    match = PVP_HIT_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.PVP_HIT,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            victim_hp=float(data["victim_hp"]) if data.get("victim_hp") else None,
            killer_name=data.get("killer"),
            killer_id=data.get("killer_id"),
            weapon=data.get("weapon", "").strip() if data.get("weapon") else None,
            ammo_type=data.get("ammo_type"),
            distance_m=float(data["distance"]) if data.get("distance") else 0.0,
            hit_location=data.get("hit_location"),
            damage_dealt=float(data["damage"]) if data.get("damage") else None,
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 2: Headshot Kill
    match = HEADSHOT_KILL_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.HEADSHOT_KILL,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            victim_hp=float(data["victim_hp"]) if data.get("victim_hp") else 0.0,
            killer_name=data.get("killer"),
            killer_id=data.get("killer_id"),
            weapon=data.get("weapon", "").strip() if data.get("weapon") else None,
            ammo_type=data.get("ammo_type"),
            distance_m=float(data["distance"]) if data.get("distance") else 0.0,
            hit_location=data.get("hit_location", "Head"),
            damage_dealt=float(data["damage"]) if data.get("damage") else None,
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 3: Melee Kill
    match = MELEE_KILL_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.MELEE_KILL,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            victim_hp=float(data["victim_hp"]) if data.get("victim_hp") else 0.0,
            killer_name=data.get("killer"),
            killer_id=data.get("killer_id"),
            weapon=data.get("weapon", "").strip() if data.get("weapon") else "Melee",
            ammo_type=data.get("ammo_type"),
            distance_m=0.0,
            hit_location=data.get("hit_location"),
            damage_dealt=float(data["damage"]) if data.get("damage") else None,
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 4: PVP Kill with Distance
    match = PVP_KILL_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.PVP_KILL,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            killer_name=data.get("killer"),
            killer_id=data.get("killer_id"),
            weapon=data.get("weapon"),
            distance_m=float(data["distance"]) if data.get("distance") else None,
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 5: Explosion Death
    match = EXPLOSION_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.EXPLOSION_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            explosive_type=data.get("explosive"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 6: Vehicle Death
    match = VEHICLE_DEATH_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.VEHICLE_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            victim_hp=float(data["victim_hp"]) if data.get("victim_hp") else 0.0,
            vehicle_type=data.get("vehicle"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 7: Fall Death
    match = FALL_DEATH_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.FALL_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 8: Bleed Death
    match = BLEED_DEATH_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.BLEED_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            bleed_count=int(data["bleed_count"]) if data.get("bleed_count") else None,
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 9: Suicide
    match = SUICIDE_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.SUICIDE,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 10: Disconnect/Rage Quit
    match = DISCONNECT_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.DISCONNECT_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 11: Animal Death (check BEFORE Zombie to avoid false matches)
    match = ANIMAL_DEATH_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.ANIMAL_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            animal_type=data.get("animal_type"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # Priority 12: Zombie Death
    match = ZOMBIE_DEATH_PATTERN.search(raw)
    if match:
        data = match.groupdict()
        victim_x, victim_y, victim_z = _extract_position(data.get("victim_pos", ""))

        return ParsedCombatEvent(
            event_type=CombatEventType.ZOMBIE_DEATH,
            timestamp=data.get("timestamp") or timestamp,
            victim_name=data["victim"],
            victim_id=data.get("victim_id"),
            location_x=victim_x,
            location_y=victim_y,
            location_z=victim_z,
            raw_message=raw,
        )

    # If we reach here, no pattern matched
    return None


# ============================================================================
# LEGACY COMPATIBILITY (for existing code using old ParsedKillEvent)
# ============================================================================


# Keep old dataclass for backward compatibility
@dataclass
class ParsedKillEvent:
    timestamp: str
    killer: str
    victim: str
    weapon: str | None
    distance_m: float | None
    location: str | None
    raw: str


def parse_kill_event(message: str) -> ParsedKillEvent | None:
    """
    Legacy parser for backward compatibility.
    This will eventually be deprecated in favor of parse_combat_event.
    """
    # Use new parser and convert to old format
    event = parse_combat_event(message)
    if not event:
        return None

    # Only return if it's a PVP kill event
    if not event.is_pvp() or not event.is_kill():
        return None

    location = None
    if event.location_x and event.location_y:
        location = f"{int(event.location_x)},{int(event.location_y)}"

    return ParsedKillEvent(
        timestamp=event.timestamp,
        killer=event.killer_name or "",
        victim=event.victim_name,
        weapon=event.weapon,
        distance_m=event.distance_m,
        location=location,
        raw=event.raw_message,
    )


# ============================================================================
# KILLFEED MANAGER
# ============================================================================


class KillfeedManager:
    """Routes combat log events to separate Discord channels (PVP vs. PVE)."""

    def __init__(
        self,
        bot: discord.Client,
        kill_channel_id: int,
        death_channel_id: int | None = None,
        db: Database | None = None,
    ) -> None:
        self.bot = bot
        self.kill_channel_id = kill_channel_id
        self.death_channel_id = death_channel_id or kill_channel_id
        self.db = db
        self.streamer = get_streamer()
        self._listener_registered = False
        self._recent: deque[str] = deque(maxlen=200)
        self._queue: asyncio.Queue[ParsedCombatEvent] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if not self.streamer.tasks:
            await self.streamer.start()

        if not self._listener_registered:
            self.streamer.add_listener(self._handle_log_event)
            self._listener_registered = True

        if self._task is None:
            self._task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._listener_registered:
            self.streamer.remove_listener(self._handle_log_event)
            self._listener_registered = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _handle_log_event(self, event: LogEvent) -> None:
        if event.level != "combat":
            return

        payload = event.raw or event.message or ""
        parsed = parse_combat_event(payload)
        if not parsed:
            return

        # Create deduplication key
        key = f"{parsed.event_type.value}:{parsed.victim_name}:{parsed.killer_name}:{parsed.timestamp}"
        if key in self._recent:
            return
        self._recent.append(key)

        await self._queue.put(parsed)

    async def _worker(self) -> None:
        poi_manager = get_poi_manager()
        # Initialize POI manager with restored path
        if not poi_manager._initialized:
            repo_root = Path(__file__).parent.parent
            poi_path = (
                repo_root
                / "data/archives/dayz_console_mod_provenance/home/toxic/dayz_workspace/dayzxb_missions/dayzOffline.chernarusplus/cfgeventspawns.xml"
            )
            poi_manager.load_from_xml(str(poi_path))

        from .image_generator import get_image_generator

        image_generator = get_image_generator()

        while True:
            event = await self._queue.get()
            try:
                # Resolve targets
                target_channel_id = self.kill_channel_id if event.is_pvp() else self.death_channel_id

                # Dynamic fetching/caching
                target_channel = self.bot.get_channel(target_channel_id)
                if not target_channel:
                    try:
                        target_channel = await self.bot.fetch_channel(target_channel_id)
                    except:
                        pass

                if not target_channel:
                    log.error("Combat feed channel %s not found", target_channel_id)
                    continue

                # 1. Resolve Location (Custom POI)
                location_name = "Unknown Wilderness"
                if event.location_x and event.location_z:
                    poi_result = poi_manager.get_nearest_poi(event.location_x, event.location_z)
                    if poi_result:
                        poi, _dist = poi_result
                        location_name = f"Near {poi.name}"
                    else:
                        # Fallback to coordinate generic name or zone (could use a simple map grid here later)
                        location_name = f"Grid {int(event.location_x / 1000)}-{int(event.location_z / 1000)}"

                # 2. Generate Kill Card Image
                try:
                    image_bytes = await asyncio.to_thread(image_generator.generate_kill_card, event, location_name)
                    file = discord.File(io.BytesIO(image_bytes), filename="kill_card.png")

                    # 3. Send to Discord with minimal text (for search) but primary image
                    # We can use an embed color matching the event type too
                    embed_color = 0xFF0000 if event.is_pvp() else 0xCCCCCC
                    if event.event_type == CombatEventType.PVP_HIT:
                        embed_color = 0xFFA500  # Orange for hits

                    embed = discord.Embed(color=embed_color)
                    embed.set_image(url="attachment://kill_card.png")

                    # Optional footer
                    embed.set_footer(text="DayZ Combat Analytics • 2025 Edition")

                    await target_channel.send(file=file, embed=embed)

                except Exception as e:
                    log.error(f"Failed to generate/send kill card: {e}")
                    # Fallback to text only
                    content = self._format_message(event, location_name)
                    await target_channel.send(content)

                # Log to DB
                if self.db:
                    try:
                        org_id = getattr(self.bot.settings, "org_id", "unknown")

                        # Prepare position tuple
                        pos_tuple = None
                        if event.location_x is not None:
                            pos_tuple = (event.location_x, event.location_y, event.location_z)

                        await self.db.log_combat(
                            org_id=org_id,
                            killer=event.killer_name or "",
                            victim=event.victim_name,
                            weapon=event.weapon,
                            distance=event.distance_m,
                            location=location_name,
                            pos=pos_tuple,
                            raw=event.raw_message,
                        )
                    except Exception as e:
                        log.error(f"Failed to log combat to DB: {e}")

                # 4. Publish to Event Fabric (Dual-Path)
                if getattr(self.bot, "event_bus", None):
                    bus_payload = {
                        "event_type": event.event_type.value,
                        "timestamp": event.timestamp,
                        "killer": event.killer_name,
                        "victim": event.victim_name,
                        "weapon": event.weapon,
                        "distance": event.distance_m,
                        "location": location_name,
                        "coords": f"{event.location_x},{event.location_y}" if event.location_x else None,
                        "raw_message": event.raw_message,
                    }
                    await self.bot.event_bus.publish("killfeed.kill", bus_payload)

            except Exception:
                log.exception("Failed to publish combat event")
                await asyncio.sleep(5)

    def _format_message(self, event: ParsedCombatEvent, location: str = "Unknown") -> str:
        """Aesthetic text fallback and embed description."""

        # Icon based on event type
        icon_map = {
            CombatEventType.PVP_KILL: "💀",
            CombatEventType.PVP_HIT: "🩸",
            CombatEventType.HEADSHOT_KILL: "🎯",
            CombatEventType.MELEE_KILL: "🥊",
            CombatEventType.EXPLOSION_DEATH: "💥",
            CombatEventType.VEHICLE_DEATH: "🚗",
            CombatEventType.FALL_DEATH: "🪂",
            CombatEventType.BLEED_DEATH: "💉",
            CombatEventType.SUICIDE: "😵",
            CombatEventType.DISCONNECT_DEATH: "🔌",
            CombatEventType.ZOMBIE_DEATH: "🧟",
            CombatEventType.ANIMAL_DEATH: "🐻",
        }

        icon = icon_map.get(event.event_type, "☠️")

        if event.is_pvp() and event.killer_name:
            # Theme: **Killer** eliminated **Victim** [Weapon] [Distance] [Location]
            parts = [f"{icon} **{event.killer_name}** eliminated **{event.victim_name}**"]

            if event.weapon:
                parts.append(f"〖`{event.weapon}`〗")
            if event.distance_m is not None and event.distance_m > 0:
                parts.append(f"〖`{event.distance_m:.1f}m`〗")

            parts.append(f"〖📍 `{location}`〗")

            return " ".join(parts)

        else:
            # PVE death
            death_messages = {
                CombatEventType.EXPLOSION_DEATH: f"{icon} **{event.victim_name}** exploded",
                CombatEventType.VEHICLE_DEATH: f"{icon} **{event.victim_name}** was totaled",
                CombatEventType.FALL_DEATH: f"{icon} **{event.victim_name}** lost their footing",
                CombatEventType.BLEED_DEATH: f"{icon} **{event.victim_name}** bled out",
                CombatEventType.SUICIDE: f"{icon} **{event.victim_name}** tapped out",
                CombatEventType.DISCONNECT_DEATH: f"{icon} **{event.victim_name}** disconnected",
                CombatEventType.ZOMBIE_DEATH: f"{icon} **{event.victim_name}** was mauled",
                CombatEventType.ANIMAL_DEATH: f"{icon} **{event.victim_name}** was hunted",
            }

            base_msg = death_messages.get(event.event_type, f"{icon} **{event.victim_name}** died")
            return f"{base_msg} 〖📍 `{location}`〗"
