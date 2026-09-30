from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import discord
from src.mildlyawesome.core.types import CombatEvent, CombatEventType

log = logging.getLogger("mildlyawesome.services.view")

class ViewService:
    """Centralizes Discord embed generation for consistent aesthetics."""

    @staticmethod
    def create_kill_embed(event: CombatEvent) -> discord.Embed:
        """Standardized kill event embed."""
        color = 0xFF0000 if event.event_type == CombatEventType.PVP_KILL else 0xCCCCCC
        if event.event_type == CombatEventType.PVP_HIT:
            color = 0xFFA500

        embed = discord.Embed(
            title=f"{ViewService.get_event_emoji(event.event_type)} Combat Event",
            color=color,
            timestamp=event.timestamp if isinstance(event.timestamp, datetime) else datetime.now(timezone.utc)
        )

        killer_name = event.killer.gamertag if event.killer else "Environment"
        victim_name = event.victim.gamertag

        if event.is_pvp:
            embed.description = f"**{killer_name}** killed **{victim_name}**"
            if event.weapon:
                embed.add_field(name="Weapon", value=event.weapon, inline=True)
            if event.distance_m:
                embed.add_field(name="Distance", value=f"{event.distance_m:.1f}m", inline=True)
        else:
            embed.description = f"**{victim_name}** died to {killer_name}"

        embed.add_field(name="Location", value=event.location_name or "Unknown", inline=True)
        embed.set_footer(text="MildlyAwesome Combat Analytics")
        return embed

    @staticmethod
    def create_todo_embed(task: Any) -> discord.Embed:
        """Standardized TODO task card."""
        status_icons = {
            "ready": "🟦",
            "in_progress": "🟨",
            "blocked": "🟥",
            "done": "🟩",
            "dropped": "⛔️",
        }
        icon = status_icons.get(task.status, "🟦")
        priority_icons = {"P0": "🔥", "P1": "⚠️", "P2": "✳️"}
        p_icon = priority_icons.get(task.priority, "")
        
        embed = discord.Embed(
            title=f"{icon} {p_icon} [{task.priority}] {task.title}",
            color=0x2b2d31
        )
        embed.add_field(name="Scope", value=task.scope, inline=False)
        embed.add_field(name="Surface", value=f"`{task.surface}`", inline=True)
        embed.add_field(name="Acceptance", value=task.acceptance, inline=True)
        
        owner = task.owner or "—"
        embed.add_field(name="Owner", value=owner, inline=True)
        embed.set_footer(text=f"Ref: {task.task_key or f'task-{task.id}'}")
        return embed

    @staticmethod
    def create_deployment_embed(commit: Dict[str, Any], emoji: str, highlights: List[str], color: discord.Color, org_id: str) -> discord.Embed:
        """Standardized deployment impact card."""
        subject = commit['subject'][:1000] + "..." if len(commit['subject']) > 1000 else commit['subject']
        
        embed = discord.Embed(
            title=f"{emoji} Deploy: {commit['sha'][:7]}",
            description=f"```fix\n{subject}\n```",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_author(name=commit['author'], icon_url=f"https://github.com/{commit['author']}.png")
        
        if highlights:
            h_text = "\n".join(highlights[:10])
            if len(highlights) > 10: h_text += f"\n*...and {len(highlights)-10} more impacts*"
            embed.add_field(name="Impact Analysis", value=h_text[:1024], inline=False)
            
        file_list = "\n".join([f"`{f}`" for f in commit['files'][:3]])
        if len(commit['files']) > 3:
            file_list += f"\n*...and {len(commit['files']) - 3} more files*"
        
        embed.add_field(name=f"Files ({len(commit['files'])})", value=file_list or "No file changes detected", inline=True)
        embed.set_footer(text=f"DayZ Ops Engine • {org_id}")
        return embed

    @staticmethod
    def get_event_emoji(event_type: CombatEventType) -> str:
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
        return icon_map.get(event_type, "☠️")
