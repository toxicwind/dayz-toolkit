from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

import discord
from discord.ext import tasks, commands

from src.mildlyawesome.services.view import ViewService

log = logging.getLogger("mildlyawesome.bot.changefeed")

class DeploymentImpact:
    CRITICAL_PATHS = ['config/', 'compose.yaml', 'Dockerfile', 'pyproject.toml', 'bot/']
    
    @staticmethod
    def analyze(files_changed: List[str]) -> Tuple[str, str, List[str]]:
        highlights = []
        severity = "low"
        emoji = "🟢"
        
        for f in files_changed:
            if 'compose' in f:
                highlights.append("🔄 **Compose changed** — Restart likely required")
                severity = "high"
            elif 'config/' in f:
                highlights.append("⚙️ **Config changed** — YAML merge impact")
                severity = "high"
            elif 'Dockerfile' in f:
                highlights.append("🏗️ **Dockerfile changed** — Build required")
                severity = "high"
            elif 'pyproject.toml' in f:
                highlights.append("📦 **Dependencies updated**")
                severity = "medium"
        
        if severity == "high": emoji = "🔴"
        elif severity == "medium": emoji = "🟡"
        
        return severity, emoji, highlights

class ChangeFeed(commands.Cog):
    """Tracks repository deployments and posts impact cards to Discord."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_sha = None
        self.channel_id = None
        self.repo_root = Path(__file__).resolve().parents[3]

    async def _get_state(self, key: str) -> Optional[str]:
        def _sync():
            with self.bot.db._conn.cursor() as cursor:
                cursor.execute("SELECT cfg_value FROM changefeed_state WHERE cfg_key=%s", (key,))
                row = cursor.fetchone()
                return row["cfg_value"] if row else None
        return await asyncio.to_thread(_sync)

    async def _set_state(self, key: str, value: str):
        def _sync():
            with self.bot.db._conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO changefeed_state (cfg_key, cfg_value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE cfg_value=%s",
                    (key, value, value)
                )
        await asyncio.to_thread(_sync)

    async def _mark_deployed(self, sha: str):
        def _sync():
            with self.bot.db._conn.cursor() as cursor:
                cursor.execute("INSERT IGNORE INTO deployed_commits (sha) VALUES (%s)", (sha,))
        await asyncio.to_thread(_sync)

    async def _is_deployed(self, sha: str) -> bool:
        def _sync():
            with self.bot.db._conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM deployed_commits WHERE sha=%s", (sha,))
                return cursor.fetchone() is not None
        return await asyncio.to_thread(_sync)

    async def cog_load(self):
        sha = await self._get_state("last_sha")
        if sha: self.last_sha = sha
        
        cid = await self._get_state("channel_id")
        if cid: self.channel_id = int(cid)

        try:
            await self.ensure_channel()
        except Exception as e:
            log.error(f"Failed to ensure changefeed channel: {e}")
        self.poll_loop.start()

    async def cog_unload(self):
        self.poll_loop.cancel()

    async def ensure_channel(self):
        guild_id = self.bot.settings.discord_guild_id
        guild = self.bot.get_guild(guild_id)
        if not guild: return None

        channel_name = f"✨-deploy-feed"
        channel = None
        
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
        
        if not channel:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if not channel:
            channel = await guild.create_text_channel(channel_name)
            self.channel_id = channel.id
            await self._set_state("channel_id", str(channel.id))
            
            embed = discord.Embed(
                title="🚀 Change Feed Initialized",
                description="Tracking repository deployments and configuration changes.",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
        
        return channel

    async def get_commit_details(self, sha: str) -> Optional[Dict[str, Any]]:
        try:
            info = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=format:%an|||%s', sha],
                cwd=self.repo_root
            ).decode().strip().split('|||')
            
            author = info[0] if len(info) > 0 else "Unknown"
            subject = info[1] if len(info) > 1 else "Auto-commit"
            
            files = subprocess.check_output(
                ['git', 'diff', '--name-only', f'{sha}^', sha],
                cwd=self.repo_root
            ).decode().strip().split('\n')
            
            diffstat = subprocess.check_output(
                ['git', 'diff', '--stat', f'{sha}^', sha],
                cwd=self.repo_root
            ).decode().strip()
            
            return {
                "sha": sha,
                "author": author,
                "subject": subject,
                "files": [f for f in files if f],
                "diffstat": diffstat
            }
        except Exception as e:
            log.error(f"Git error for {sha}: {e}")
            return None

    @tasks.loop(seconds=120, reconnect=True)
    async def poll_loop(self):
        try:
            current_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.repo_root).decode().strip()
            
            if self.last_sha is None:
                self.last_sha = current_sha
                await self._set_state("last_sha", current_sha)
                return

            if current_sha != self.last_sha:
                commits = subprocess.check_output(
                    ['git', 'log', '--pretty=format:%H', f'{self.last_sha}..{current_sha}'],
                    cwd=self.repo_root
                ).decode().strip().split('\n')
                
                for sha in reversed(commits):
                    if not sha: continue
                    if await self._is_deployed(sha): continue
                    
                    details = await self.get_commit_details(sha)
                    if details:
                        channel = await self.ensure_channel()
                        if channel:
                            severity, emoji, highlights = DeploymentImpact.analyze(details['files'])
                            color = discord.Color.green()
                            if severity == "high": color = discord.Color.red()
                            elif severity == "medium": color = discord.Color.orange()
                            
                            embed = ViewService.create_deployment_embed(
                                details, emoji, highlights, color, 
                                getattr(self.bot.settings, "org_id", "mildlyawesome")
                            )
                            await channel.send(embed=embed)
                            await self._mark_deployed(sha)
                
                self.last_sha = current_sha
                await self._set_state("last_sha", current_sha)
        except Exception as e:
            log.error(f"Poll loop error: {e}")

    @poll_loop.before_loop
    async def before_poll_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ChangeFeed(bot))
