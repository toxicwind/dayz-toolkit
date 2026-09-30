
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
import discord
from pathlib import Path
import json
from datetime import datetime

from src.mildlyawesome.globals import get_bot
from src.mildlyawesome.discord_registry import DiscordRegistry
from src.mildlyawesome.discord_ingest_store import store as ingest_store

router = APIRouter(tags=["Discord Ops"])
log = logging.getLogger("mildlyawesome.api.discord")

# --- Models ---

class ChannelSpecUpdate(BaseModel):
    spec: Dict[str, Any]

class ChannelMatrixResponse(BaseModel):
    channels: list[dict]
    last_seq: int
    tracks: list[str]

class CategoryAuditRequest(BaseModel):
    category_id: int

class ChannelTestRequest(BaseModel):
    message: str = "Chronos Integration Test"

class DiscordBatchAction(BaseModel):
    action: str  # "send", "delete", "create"
    target: str | int
    payload: Dict[str, Any] | str | None = None

class DiscordBatchRequest(BaseModel):
    actions: List[DiscordBatchAction]
    parallel: bool = False

# --- Endpoints ---

@router.post("/discord/reconstitute")
async def discord_reconstitute_endpoint(dry_run: bool = False, nuke: bool = False):
    """
    Trigger the Chronos Reconstitution (Sync) process.
    Forces the Guild topology to match `discord/channel_spec.json`.
    """
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}

    repo_root = Path(__file__).parent.parent.parent.parent
    registry = DiscordRegistry(repo_root)

    guild = bot.get_guild(bot.settings.discord_guild_id)
    if not guild:
         return {"status": "error", "message": "Target Guild not found"}

    try:
        results = {}
        if nuke:
            results["nuke"] = await registry.nuke(guild, dry_run=dry_run)

        results["sync"] = await registry.sync(guild, dry_run=dry_run)
        return {"status": "ok", "dry_run": dry_run, "results": results}
    except Exception as e:
        log.error(f"Reconstitution failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/discord/batch")
async def discord_batch_endpoint(batch: DiscordBatchRequest):
    """
    Execute multiple Discord operations in sequence or parallel with rate-limit awareness.
    """
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot not connected"}

    results = []

    async def run_action(action: DiscordBatchAction):
        try:
            if action.action == "send":
                channel = bot.get_channel(int(action.target))
                if channel and hasattr(channel, "send"):
                    msg = await channel.send(str(action.payload))
                    return {"action": "send", "target": action.target, "status": "ok", "id": msg.id}
                return {"action": "send", "target": action.target, "status": "error", "message": "Channel not found"}

            elif action.action == "delete":
                channel = bot.get_channel(int(action.target))
                if channel:
                    await channel.delete(reason="Batch Operation")
                    return {"action": "delete", "target": action.target, "status": "ok"}
                return {"action": "delete", "target": action.target, "status": "error", "message": "Channel not found"}

            elif action.action == "create":
                # payload = {"name": "...", "category_id": 123}
                guild = bot.get_guild(bot.settings.discord_guild_id)
                p = action.payload or {}
                cat = guild.get_channel(int(p.get("category_id"))) if p.get("category_id") else None
                chan = await guild.create_text_channel(name=str(p.get("name", "new-channel")), category=cat)
                return {"action": "create", "status": "ok", "id": chan.id}

            return {"action": action.action, "status": "unsupported"}
        except Exception as e:
            return {"action": action.action, "status": "exception", "message": str(e)}

    if batch.parallel:
        results = await asyncio.gather(*(run_action(a) for a in batch.actions))
    else:
        for a in batch.actions:
            res = await run_action(a)
            results.append(res)
            await asyncio.sleep(0.5) # Basic rate limit spacing

    return {"status": "completed", "results": results}

@router.get("/discord/spec")
async def get_discord_spec():
    """Return the current declarative channel specification."""
    repo_root = Path(__file__).parent.parent.parent.parent
    registry = DiscordRegistry(repo_root)
    return registry.spec

@router.get("/discord/state")
async def get_discord_state():
    """Return the current authoritative channel ID map."""
    repo_root = Path(__file__).parent.parent.parent.parent
    registry = DiscordRegistry(repo_root)
    return registry.state

@router.post("/discord/spec")
async def update_discord_spec(update: ChannelSpecUpdate):
    """Update the channel specification (Hot)."""
    repo_root = Path(__file__).parent.parent.parent.parent
    registry = DiscordRegistry(repo_root)
    registry.spec = update.spec

    with open(registry.spec_path, "w") as f:
        json.dump(update.spec, f, indent=2)

    return {"status": "ok", "message": "Spec updated. Run /discord/reconstitute to apply."}

@router.get("/discord/diagnostics", response_model=ChannelMatrixResponse)
async def discord_diagnostics():
    """Return channel validation status + last event cursors."""
    status = ingest_store.get_status_matrix()
    tracks = []
    bot = get_bot()
    if bot and getattr(bot, "_tracked_channels", None):
        tracks = list(bot._tracked_channels().keys())
    return ChannelMatrixResponse(
        channels=status.get("channels", []),
        last_seq=status.get("last_seq", 0),
        tracks=tracks
    )

@router.post("/discord/audit/category")
async def audit_discord_category_endpoint(req: CategoryAuditRequest):
    """Audit any Discord Category by ID."""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}

    target_cat = None

    for guild in bot.guilds:
        cat = guild.get_channel(req.category_id)
        if cat:
            target_cat = cat
            break

    if not target_cat:
        try:
           target_cat = await bot.fetch_channel(req.category_id)
        except Exception:
           pass

    if not target_cat:
        return {"status": "error", "message": f"Category {req.category_id} not found"}

    if not isinstance(target_cat, discord.CategoryChannel):
        return {"status": "error", "message": f"ID {req.category_id} is {type(target_cat)}, not a Category"}

    channels_data = []
    for c in sorted(target_cat.channels, key=lambda x: x.position):
        channels_data.append({
            "id": str(c.id),
            "name": c.name,
            "type": str(c.type),
            "position": c.position,
            "topic": getattr(c, "topic", None),
            "nsfw": getattr(c, "nsfw", False)
        })

    return {
        "status": "ok",
        "category": {
            "id": str(target_cat.id),
            "name": target_cat.name,
            "guild": target_cat.guild.name,
            "channel_count": len(channels_data)
        },
        "channels": channels_data
    }

@router.get("/tools/discord/audit")
async def tool_discord_audit_endpoint():
    """Run a full Discord Guild Audit."""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}

    guild_id = bot.settings.discord_guild_id
    if not guild_id:
        return {"status": "error", "message": "Bot Guild ID not configured"}

    guild = bot.get_guild(guild_id)
    if not guild:
        return {"status": "error", "message": f"Guild {guild_id} not found/cached"}

    data = {
        "guild": {"id": str(guild.id), "name": guild.name},
        "roles": [
            {"id": str(r.id), "name": r.name, "permissions": r.permissions.value}
            for r in guild.roles
        ],
        "categories": [],
        "channels": []
    }

    for cat in guild.categories:
        data["categories"].append({
            "id": str(cat.id),
            "name": cat.name,
            "position": cat.position
        })

    for channel in guild.channels:
         if isinstance(channel, discord.CategoryChannel): continue
         data["channels"].append({
             "id": str(channel.id),
             "name": channel.name,
             "type": str(channel.type),
             "category_id": str(channel.category_id) if channel.category else None,
             "position": channel.position
         })

    return data

@router.post("/tools/discord/test_channels")
async def tool_test_channels_endpoint(req: ChannelTestRequest):
    """Test write access to tracked channels."""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot instance not linked"}

    results = {}
    channels_map = bot._tracked_channels()

    for name, cid in channels_map.items():
        if not cid:
            results[name] = "Skipped (No ID)"
            continue

        channel = bot.get_channel(int(cid))
        if not channel:
            results[name] = f"Error: Channel {cid} not found"
            continue

        try:
            msg = await channel.send(f"🔧 **Chronos Diagnostics**\n{req.message}\n`Timestamp: {datetime.utcnow().isoformat()}`")
            results[name] = f"Success (MsgID: {msg.id})"
        except Exception as e:
            results[name] = f"Failed: {str(e)}"

    return {"status": "completed", "results": results}

# --- Discord Channel Inspection ---

KNOWN_CHANNELS = {
    "casino": 1452554475909812366,
    "killfeed": 1453504155388874906,
    "deathfeed": 1453504309634531490,
    "status": 1453978341076893868,
    "todo": 1454568932051783918,
    "admin": 1454365351365316713,
    "sandbox": 1454646232374055116,
    "deploy": 1454362669510561854,
}

@router.get("/discord/channels/list")
async def discord_list_channels(category: str | None = None):
    """List all accessible Discord channels in the guild"""
    bot = get_bot()
    if not bot:
        return {"status": "error", "message": "Bot not connected"}

    guild = bot.get_guild(bot.settings.discord_guild_id)
    if not guild:
         for g in bot.guilds:
             if g.id == bot.settings.discord_guild_id:
                 guild = g
                 break
    if not guild:
        return {"status": "error", "message": "Guild not found"}

    channels = []
    for ch in guild.channels:
        ch_data = {
            "id": ch.id,
            "name": ch.name,
            "type": str(ch.type),
            "category": ch.category.name if ch.category else None,
            "category_id": ch.category.id if ch.category else None,
        }
        if category and ch.category:
            if category.lower() not in ch.category.name.lower():
                continue
        channels.append(ch_data)

    return {"status": "ok", "guild": guild.name, "channels": channels, "count": len(channels)}

@router.get("/discord/channels/{channel_id}")
async def discord_get_channel(channel_id: int):
    """Get info about a specific Discord channel"""
    bot = get_bot()
    if not bot: return {"status": "error", "message": "Bot not connected"}
    channel = bot.get_channel(channel_id)
    if not channel: return {"status": "error", "message": f"Channel {channel_id} not found"}
    return {
        "status": "ok",
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "type": str(channel.type),
            "category": channel.category.name if channel.category else None,
            "topic": getattr(channel, "topic", None),
            "created_at": channel.created_at.isoformat() if channel.created_at else None,
        },
    }

@router.get("/discord/channels/{channel_id}/messages")
async def discord_get_messages(channel_id: int, limit: int = 10):
    """Read recent messages from a Discord channel."""
    bot = get_bot()
    if not bot: return {"status": "error", "message": "Bot not connected"}
    channel = bot.get_channel(channel_id)
    if not channel: return {"status": "error", "message": f"Channel {channel_id} not found"}
    if not hasattr(channel, "history"): return {"status": "error", "message": "Channel does not support history"}
    try:
        messages = []
        async for msg in channel.history(limit=min(limit, 50)):
            messages.append({
                "id": msg.id,
                "author": msg.author.name,
                "author_id": msg.author.id,
                "content": msg.content[:500] if msg.content else "",
                "timestamp": msg.created_at.isoformat(),
                "embeds": len(msg.embeds),
            })
        return {"status": "ok", "channel_name": channel.name, "messages": messages}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/discord/inspect/{channel_name}")
async def discord_inspect_named_channel(channel_name: str, limit: int = 10):
    """Inspect a known channel by name (casino, killfeed, etc.)"""
    channel_id = KNOWN_CHANNELS.get(channel_name.lower())
    if not channel_id:
        return {"status": "error", "message": f"Unknown channel name: {channel_name}"}
    return await discord_get_messages(channel_id, limit)

@router.post("/discord/channels/{channel_id}/send")
async def discord_send_message(channel_id: int, content: str = Body(..., embed=True)):
    """Send a message to a Discord channel"""
    bot = get_bot()
    if not bot: return {"status": "error", "message": "Bot not connected"}
    channel = bot.get_channel(channel_id)
    if not channel or not hasattr(channel, "send"):
        return {"status": "error", "message": "Channel not found or not sendable"}
    try:
        msg = await channel.send(content)
        return {"status": "ok", "message_id": msg.id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
