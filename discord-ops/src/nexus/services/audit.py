from __future__ import annotations

import discord
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

log = logging.getLogger("mildlyawesome.services.audit")

CHANNEL_FEATURE_MAP = {
    "status_board": ["status", "server-status", "🟢"],
    "killfeed": ["killfeed", "kill-feed", "combat", "💀"],
    "changefeed": ["deploy", "changes", "feed", "✨"],
    "selfplay": ["selfplay", "🧪"],
    "trader": ["trader", "shop", "market", "💰"],
    "tickets": ["ticket", "support", "🎫"],
    "casino": ["casino", "gambling", "🎰"],
    "bank": ["bank", "economy", "💵"],
    "leaderboard": ["leaderboard", "stats", "🏆"],
    "announcements": ["announce", "news", "📢"],
}

@dataclass
class ChannelAuditResult:
    channel_id: int
    channel_name: str
    channel_type: str
    category: Optional[str]
    matched_feature: Optional[str]
    suggestions: List[str]

class AuditService:
    """Hardened logic for auditing Discord guild structures and feature mapping."""
    
    @staticmethod
    def audit_channels(guild: discord.Guild) -> Dict[str, Any]:
        results: List[ChannelAuditResult] = []
        matched_channels: Dict[str, List[str]] = {}
        unmatched_channels: List[Tuple[str, int]] = []

        for channel in guild.channels:
            channel_name_lower = channel.name.lower()
            category_name = channel.category.name if channel.category else "No Category"
            ch_type = AuditService._get_channel_type(channel)

            matched_feature = None
            for feature, patterns in CHANNEL_FEATURE_MAP.items():
                if any(p.lower() in channel_name_lower for p in patterns):
                    matched_feature = feature
                    matched_channels.setdefault(feature, []).append(f"#{channel.name}")
                    break

            suggestions = []
            if not matched_feature and ch_type == "text":
                unmatched_channels.append((channel.name, channel.id))
                suggestions = AuditService._get_suggestions(channel_name_lower)

            results.append(ChannelAuditResult(
                channel_id=channel.id,
                channel_name=channel.name,
                channel_type=ch_type,
                category=category_name,
                matched_feature=matched_feature,
                suggestions=suggestions
            ))
            
        return {
            "results": results,
            "matched_channels": matched_channels,
            "unmatched_channels": unmatched_channels,
            "stats": {
                "total": len(guild.channels),
                "matched": sum(len(v) for v in matched_channels.values()),
                "unmatched": len(unmatched_channels)
            }
        }

    @staticmethod
    def _get_channel_type(channel: discord.abc.GuildChannel) -> str:
        if isinstance(channel, discord.TextChannel): return "text"
        if isinstance(channel, discord.VoiceChannel): return "voice"
        if isinstance(channel, discord.CategoryChannel): return "category"
        if isinstance(channel, discord.ForumChannel): return "forum"
        if isinstance(channel, discord.StageChannel): return "stage"
        return "unknown"

    @staticmethod
    def _get_suggestions(name_lower: str) -> List[str]:
        if "general" in name_lower: return ["Bot announcements"]
        if "admin" in name_lower: return ["Admin logs/alerts"]
        if "bot" in name_lower: return ["Dedicated bot channel"]
        return ["No automatic mapping"]
