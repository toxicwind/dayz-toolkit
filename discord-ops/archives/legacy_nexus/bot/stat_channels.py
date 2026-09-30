from __future__ import annotations

import json
from dataclasses import dataclass
import logging

import discord

log = logging.getLogger("dayz-discord-ops")

@dataclass(frozen=True)
class StatChannelConfig:
    members_total: int | None = None
    members_online: int | None = None
    dayz_players: int | None = None

def parse_stat_channels(raw: str | None) -> StatChannelConfig:
    if not raw:
        return StatChannelConfig()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"Failed to parse STAT_CHANNELS_JSON: {raw!r}")
        return StatChannelConfig()
        
    return StatChannelConfig(
        members_total=int(data["members_total"]) if "members_total" in data else None,
        members_online=int(data["members_online"]) if "members_online" in data else None,
        dayz_players=int(data["dayz_players"]) if "dayz_players" in data else None,
    )

async def _rename(guild: discord.Guild, channel_id: int, new_name: str) -> None:
    ch = guild.get_channel(channel_id)
    if not ch:
        log.warning(f"Channel {channel_id} not found in guild {guild.id}")
        return
    
    if ch.name == new_name:
        return
        
    try:
        log.info(f"Renaming channel {channel_id} ('{ch.name}') -> '{new_name}'")
        await ch.edit(name=new_name, reason="dayz-discord-ops stat update")
        log.info(f"Successfully renamed channel {channel_id} to '{new_name}'")
    except discord.Forbidden:
        log.error(f"Missing permissions to rename channel {channel_id}")
    except discord.HTTPException as e:
        log.error(f"Failed to rename channel {channel_id}: {e}")

async def update_stat_channels(
    guild: discord.Guild,
    cfg: StatChannelConfig,
    *,
    members_total: int,
    members_online: int | None,
    dayz_players: int | None,
    dayz_max_players: int | None = None,
) -> None:
    log.info(f"Updating stats: Members={members_total}, Online={members_online}, DayZ={dayz_players}/{dayz_max_players}")
    if cfg.members_total:
        await _rename(guild, cfg.members_total, f"👥 Members: {members_total}")
    if cfg.members_online:
        await _rename(
            guild,
            cfg.members_online,
            "🟢 Online: (intents off)" if members_online is None else f"🟢 Online: {members_online}",
        )
    if cfg.dayz_players:
        if dayz_players is None:
            name = "🎮 DayZ: (unavailable)"
        elif dayz_max_players is not None:
            name = f"🎮 DayZ: {dayz_players} / {dayz_max_players}"
        else:
            name = f"🎮 DayZ: {dayz_players}"
        await _rename(guild, cfg.dayz_players, name)
