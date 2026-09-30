import discord
from discord.ext import tasks, commands
import asyncio
import logging
import sqlite3
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

log = logging.getLogger(__name__)

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
    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path("state/changefeed.db")
        self.last_sha = None
        self.channel_id = None
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deployed_commits (
                sha TEXT PRIMARY KEY,
                processed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        
        cursor = conn.execute("SELECT value FROM state WHERE key = 'last_sha'")
        row = cursor.fetchone()
        if row: self.last_sha = row[0]
        
        cursor = conn.execute("SELECT value FROM state WHERE key = 'channel_id'")
        row = cursor.fetchone()
        if row and row[0] and row[0] != "None":
            self.channel_id = int(row[0])
        else:
            self.channel_id = None
        conn.close()

    def _save_state(self):
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('last_sha', ?)", (str(self.last_sha),))
        conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('channel_id', ?)", (str(self.channel_id),))
        conn.commit()
        conn.close()

    def _mark_deployed(self, sha: str):
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.execute("INSERT OR IGNORE INTO deployed_commits (sha, processed_at) VALUES (?, ?)", (sha, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    def _is_deployed(self, sha: str) -> bool:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        cursor = conn.execute("SELECT 1 FROM deployed_commits WHERE sha = ?", (sha,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    async def cog_load(self):
        self.channel_id = None # Reload from DB or find again
        self._init_db() # Re-init to be safe
        # Ensure channel exists immediately
        try:
            await self.ensure_channel()
        except Exception as e:
            log.error(f"Failed to ensure changefeed channel: {e}")
        self.poll_loop.start()

    async def cog_unload(self):
        self.poll_loop.cancel()

    async def ensure_channel(self):
        guild_id = self.bot.settings.discord.guild_id
        if not guild_id: return
        guild = self.bot.get_guild(guild_id)
        if not guild: return

        channel_name = f"✨-{self.bot.settings.org_id}-deploy-feed"
        channel = None
        
        # 1. Memory
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
        
        # 2. Config
        if not channel and getattr(self.bot.settings.discord, 'changefeed_channel_id', None):
            channel = self.bot.get_channel(self.bot.settings.discord.changefeed_channel_id)
            if channel:
                self.channel_id = channel.id
                self._save_state()

        # 3. Name fallback
        if not channel:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        # 4. Create missing
        if not channel:
            channel = await guild.create_text_channel(channel_name)
            self.channel_id = channel.id
            self._save_state()
            
            # Prelim test message
            embed = discord.Embed(
                title="🚀 Change Feed Initialized",
                description="This channel will now track all repository deployments and configuration changes.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"DayZ Ops Engine • {self.bot.settings.org_id}")
            await channel.send(embed=embed)
        
        return channel

    async def get_commit_details(self, sha: str) -> Dict:
        repo_root = Path(__file__).parent.parent.parent
        try:
            # Info
            info = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=format:%an|||%s', sha],
                cwd=repo_root
            ).decode().strip().split('|||')
            
            author = info[0] if len(info) > 0 else "Unknown"
            subject = info[1] if len(info) > 1 else "Auto-commit"
            
            # Files
            files = subprocess.check_output(
                ['git', 'diff', '--name-only', f'{sha}^', sha],
                cwd=repo_root
            ).decode().strip().split('\n')
            
            # Diffstat
            diffstat = subprocess.check_output(
                ['git', 'diff', '--stat', f'{sha}^', sha],
                cwd=repo_root
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

    async def post_card(self, commit: Dict):
        channel = await self.ensure_channel()
        if not channel: return
        
        severity, emoji, highlights = DeploymentImpact.analyze(commit['files'])
        
        color = discord.Color.green()
        if severity == "high": color = discord.Color.red()
        elif severity == "medium": color = discord.Color.orange()
        
        subject = commit['subject'][:1000] + "..." if len(commit['subject']) > 1000 else commit['subject']
        
        embed = discord.Embed(
            title=f"{emoji} Deploy: {commit['sha'][:7]}",
            description=f"```fix\n{subject}\n```",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(name=commit['author'], icon_url=f"https://github.com/{commit['author']}.png")
        
        if highlights:
            h_text = "\n".join(highlights[:10])
            if len(highlights) > 10: h_text += f"\n*...and {len(highlights)-10} more impacts*"
            embed.add_field(name="Impact Analysis", value=h_text[:1024], inline=False)
            
        file_list = "\n".join([f"`{f}`" for f in commit['files'][:3]])
        if len(commit['files']) > 3:
            file_list += f"\n*...and {len(commit['files']) - 3} more files*"
        
        # Ensure file_list itself isn't too long
        if len(file_list) > 1000:
            file_list = file_list[:990] + "..."
        
        embed.add_field(name=f"Files ({len(commit['files'])})", value=file_list or "No file changes detected", inline=True)
        
        if commit['diffstat']:
            stat_lines = commit['diffstat'].split('\n')
            last_line = stat_lines[-1] if stat_lines else ""
            embed.add_field(name="Stat", value=f"`{last_line.strip()[:100]}`", inline=True)

        embed.set_footer(text=f"DayZ Ops Engine • {self.bot.settings.org_id}")
        
        await channel.send(embed=embed)
        self._mark_deployed(commit['sha'])

    @tasks.loop(seconds=120, reconnect=True)
    async def poll_loop(self):
        repo_root = Path(__file__).parent.parent.parent
        try:
            current_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_root).decode().strip()
            
            if self.last_sha is None:
                self.last_sha = current_sha
                self._save_state()
                return

            if current_sha != self.last_sha:
                # Find commits between last and current
                commits = subprocess.check_output(
                    ['git', 'log', '--pretty=format:%H', f'{self.last_sha}..{current_sha}'],
                    cwd=repo_root
                ).decode().strip().split('\n')
                
                for sha in reversed(commits):
                    if not sha: continue
                    if self._is_deployed(sha): continue
                    
                    details = await self.get_commit_details(sha)
                    if details:
                        await self.post_card(details)
                
                self.last_sha = current_sha
                self._save_state()
                
        except Exception as e:
            log.error(f"Poll loop error: {e}")

    @poll_loop.before_loop
    async def before_poll_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ChangeFeed(bot))
