from __future__ import annotations

import asyncio
import logging
import re

import pymysql
from pymysql.cursors import DictCursor

from .config import Settings

log = logging.getLogger("dayz-discord-ops.db")


async def get_db_connection(settings: Settings):
    """
    Async helper that returns an established PyMySQL connection.
    Historically this returned a coroutine that callers forgot to await,
    so we now enforce awaiting at the boundary to avoid un-awaited
    coroutines and partially constructed connections.
    """
    db = Database(settings)
    return await db.connect()


class Database:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._conn = None

    async def connect(self):
        if not self._settings.mysql_host:
            log.warning("MySQL host not configured. Database logging disabled.")
            return None

        def _sync_connect():
            try:
                self._conn = pymysql.connect(
                    host=self._settings.mysql_host,
                    port=self._settings.mysql_port,
                    user=self._settings.mysql_user,
                    password=self._settings.mysql_pass,
                    database=self._settings.mysql_db,
                    cursorclass=DictCursor,
                    autocommit=True,
                )
                return self._conn
            except Exception as e:
                log.error(f"Failed to connect to MySQL: {e}")
                return None

        conn = await asyncio.to_thread(_sync_connect)
        if conn:
            log.info(
                f"Connected to MySQL database: {self._settings.mysql_user}@{self._settings.mysql_host}/{self._settings.mysql_db}"
            )
            await self.init_schema()
        return conn

    async def init_schema(self):
        if not self._conn:
            return

        tables = {
            "player_stats": [
                "CREATE TABLE IF NOT EXISTS player_stats (id INT AUTO_INCREMENT PRIMARY KEY)",
                "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL AFTER id",
                "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS timestamp DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS player_count INT NOT NULL",
                "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS max_players INT NOT NULL",
            ],
            "player_profiles": [
                "CREATE TABLE IF NOT EXISTS player_profiles (player_id VARCHAR(100) NOT NULL)",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL",
                "ALTER TABLE player_profiles ADD PRIMARY KEY (org_id, player_id)",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS last_known_name VARCHAR(100)",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS first_seen DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS kills INT DEFAULT 0",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS deaths INT DEFAULT 0",
                "ALTER TABLE player_profiles ADD COLUMN IF NOT EXISTS kd_ratio FLOAT GENERATED ALWAYS AS (kills / NULLIF(deaths, 0)) VIRTUAL",
            ],
            "activity_logs": [
                "CREATE TABLE IF NOT EXISTS activity_logs (id INT AUTO_INCREMENT PRIMARY KEY)",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL AFTER id",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS timestamp DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS action VARCHAR(100)",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS message TEXT NOT NULL",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS level VARCHAR(20) DEFAULT 'info'",
                "ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'info'",
            ],
            "combat_logs": [
                "CREATE TABLE IF NOT EXISTS combat_logs (id INT AUTO_INCREMENT PRIMARY KEY)",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL AFTER id",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS timestamp DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS killer VARCHAR(100) NOT NULL",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS victim VARCHAR(100) NOT NULL",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS weapon VARCHAR(100)",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS distance_m FLOAT",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS location VARCHAR(100)",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS pos_x FLOAT",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS pos_y FLOAT",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS pos_z FLOAT",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS raw_message TEXT NOT NULL",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS killer_id VARCHAR(100)",
                "ALTER TABLE combat_logs ADD COLUMN IF NOT EXISTS victim_id VARCHAR(100)",
            ],
            "economy": [
                "CREATE TABLE IF NOT EXISTS economy (user_id VARCHAR(50) PRIMARY KEY)",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL FIRST",
                "ALTER TABLE economy DROP PRIMARY KEY",
                "ALTER TABLE economy ADD PRIMARY KEY (org_id, user_id)",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS gamertag VARCHAR(100)",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS balance FLOAT DEFAULT 0.0",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS last_pos_x FLOAT",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS last_pos_y FLOAT",
                "ALTER TABLE economy ADD COLUMN IF NOT EXISTS last_pos_z FLOAT",
            ],
            "transactions": [
                "CREATE TABLE IF NOT EXISTS transactions (id INT AUTO_INCREMENT PRIMARY KEY)",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL AFTER id",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS user_id VARCHAR(50)",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS item_name VARCHAR(100)",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS cost FLOAT",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS timestamp DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'COMPLETED'",
            ],
            "tickets": [
                "CREATE TABLE IF NOT EXISTS tickets (ticket_id INT AUTO_INCREMENT PRIMARY KEY)",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS org_id VARCHAR(100) NOT NULL AFTER ticket_id",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS user_id VARCHAR(50) NOT NULL",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS channel_id VARCHAR(50) NOT NULL",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'OPEN'",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS closed_at DATETIME",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS transcript TEXT",
            ],
            "tenants": [
                "CREATE TABLE IF NOT EXISTS tenants (org_id VARCHAR(100) PRIMARY KEY)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS name VARCHAR(100) NOT NULL",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS dayz_host VARCHAR(100)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS dayz_query_port INT",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS dayz_rcon_port INT",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS dayz_rcon_password VARCHAR(100)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS nitrado_service_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS guild_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS killfeed_enabled BOOLEAN DEFAULT FALSE",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS killfeed_channel_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS restart_channel_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS changelog_channel_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS deploy_feed_channel_id VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stat_channels_json TEXT",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            ],
        }

        def _sync_init():
            try:
                with self._conn.cursor() as cursor:
                    for table, steps in tables.items():
                        for sql in steps:
                            try:
                                clean_sql = re.sub(
                                    r"(ALTER TABLE \w+ ADD COLUMN) IF NOT EXISTS",
                                    r"\1",
                                    sql,
                                    flags=re.IGNORECASE,
                                )
                                clean_sql = re.sub(
                                    r"(ALTER TABLE \w+ ADD) IF NOT EXISTS",
                                    r"\1",
                                    clean_sql,
                                    flags=re.IGNORECASE,
                                )
                                cursor.execute(clean_sql)
                            except Exception as inner_e:
                                if hasattr(inner_e, "args") and inner_e.args[0] in (1060, 1061, 1068, 1091):
                                    continue
                                log.warning(f"Migration step failed for {table}: {inner_e}")
                log.info("Database schema migration/initialization complete")
            except Exception as e:
                log.error(f"Failed to initialize schema: {e}")

        await asyncio.to_thread(_sync_init)

    async def log_stats(self, org_id: str, players: int, max_players: int):
        if not self._conn and not await self.connect():
            return

        def _sync_log():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO player_stats (org_id, player_count, max_players) VALUES (%s, %s, %s)",
                        (org_id, players, max_players),
                    )
                log.info(f"Logged stats for {org_id}: {players}/{max_players}")
            except Exception as e:
                log.error(f"Failed to log stats: {e}")

        await asyncio.to_thread(_sync_log)

    async def log_activity(self, org_id: str, activity_type: str, message: str, severity: str = "info"):
        if not self._conn and not await self.connect():
            return

        def _sync_log():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO activity_logs (org_id, type, message, severity) VALUES (%s, %s, %s, %s)",
                        (org_id, activity_type, message, severity),
                    )
            except Exception as e:
                log.error(f"Failed to log activity: {e}")

        await asyncio.to_thread(_sync_log)

    async def log_combat(
        self,
        org_id: str,
        killer: str,
        victim: str,
        killer_id: str | None = None,
        victim_id: str | None = None,
        weapon: str | None = None,
        distance: float | None = None,
        location: str | None = None,
        pos: tuple | None = None,
        raw: str = "",
    ):
        if not self._conn and not await self.connect():
            return

        def _sync_log():
            try:
                self._conn.ping(reconnect=True)
                px, py, pz = (None, None, None)
                if pos:
                    px, py, pz = pos
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO combat_logs (org_id, killer, victim, killer_id, victim_id, weapon, distance_m, location, pos_x, pos_y, pos_z, raw_message)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (org_id, killer, victim, killer_id, victim_id, weapon, distance, location, px, py, pz, raw),
                    )
            except Exception as e:
                log.error(f"Failed to log combat: {e}")

        await asyncio.to_thread(_sync_log)

    async def log_building(
        self,
        org_id: str,
        player_name: str,
        action: str,
        structure: str,
        pos_x: float | None = None,
        pos_z: float | None = None,
        tool: str | None = None,
    ):
        if not self._conn and not await self.connect():
            return

        def _sync_log():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO activity_logs (org_id, type, action, message, severity)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            org_id,
                            "BUILDING",
                            action,
                            f"{player_name} {action} {structure} at {pos_x}, {pos_z} with {tool}",
                            "info",
                        ),
                    )
            except Exception as e:
                log.error(f"Failed to log building: {e}")

        await asyncio.to_thread(_sync_log)

    async def update_player_pos(self, org_id: str, gamertag: str, x: float, y: float, z: float):
        if not self._conn and not await self.connect():
            return

        def _sync_update():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        """UPDATE economy SET last_pos_x=%s, last_pos_y=%s, last_pos_z=%s
                           WHERE gamertag=%s AND org_id=%s""",
                        (x, y, z, gamertag, org_id),
                    )
            except Exception as e:
                log.error(f"Failed to update player pos: {e}")

        await asyncio.to_thread(_sync_update)

    async def get_balance(self, org_id: str, user_id: str) -> float:
        if not self._conn and not await self.connect():
            return 0.0

        def _sync_get():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute("SELECT balance FROM economy WHERE user_id=%s AND org_id=%s", (user_id, org_id))
                    row = cursor.fetchone()
                    return row["balance"] if row else 0.0
            except Exception:
                return 0.0

        return await asyncio.to_thread(_sync_get)

    async def update_balance(self, org_id: str, user_id: str, amount: float) -> bool:
        if not self._conn and not await self.connect():
            return False

        def _sync_update():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO economy (org_id, user_id, balance) VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE balance = balance + %s""",
                        (org_id, user_id, amount, amount),
                    )
                return True
            except Exception as e:
                log.error(f"Failed to update balance: {e}")
                return False

        return await asyncio.to_thread(_sync_update)

    async def get_user_data(self, org_id: str, user_id: str):
        if not self._conn and not await self.connect():
            return None

        def _sync_get():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM economy WHERE user_id=%s AND org_id=%s", (user_id, org_id))
                    return cursor.fetchone()
            except Exception:
                return None

        return await asyncio.to_thread(_sync_get)

    async def create_ticket(self, user_id: str, channel_id: str) -> int:
        if not self._conn and not await self.connect():
            return -1

        def _sync_create():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute("INSERT INTO tickets (user_id, channel_id) VALUES (%s, %s)", (user_id, channel_id))
                    return cursor.lastrowid
            except Exception as e:
                log.error(f"Failed to create ticket: {e}")
                return -1

        return await asyncio.to_thread(_sync_create)

    async def close_ticket(self, channel_id: str, transcript: str | None = None):
        if not self._conn and not await self.connect():
            return

        def _sync_close():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE tickets SET status='CLOSED', closed_at=NOW(), transcript=%s WHERE channel_id=%s AND status='OPEN'",
                        (transcript, channel_id),
                    )
            except Exception as e:
                log.error(f"Failed to close ticket: {e}")

        await asyncio.to_thread(_sync_close)

    async def update_player_profile(self, org_id: str, player_id: str, name: str):
        if not self._conn and not await self.connect():
            return

        def _sync_update():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    # Upsert profile
                    cursor.execute(
                        """INSERT INTO player_profiles (org_id, player_id, last_known_name)
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE last_known_name=%s, last_seen=NOW()""",
                        (org_id, player_id, name, name),
                    )
            except Exception as e:
                log.error(f"Failed to update profile {player_id}: {e}")

        await asyncio.to_thread(_sync_update)

    async def increment_kill_stats(self, org_id: str, killer_id: str, victim_id: str):
        if not self._conn and not await self.connect():
            return

        def _sync_stats():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    if killer_id and killer_id != "Unknown":
                        cursor.execute(
                            "UPDATE player_profiles SET kills = kills + 1 WHERE org_id=%s AND player_id=%s",
                            (org_id, killer_id),
                        )
                    if victim_id and victim_id != "Unknown":
                        cursor.execute(
                            "UPDATE player_profiles SET deaths = deaths + 1 WHERE org_id=%s AND player_id=%s",
                            (org_id, victim_id),
                        )
            except Exception as e:
                log.error(f"Failed to increment stats: {e}")

        await asyncio.to_thread(_sync_stats)

    async def get_ticket(self, channel_id: str):
        if not self._conn and not await self.connect():
            return None

        def _sync_get():
            try:
                self._conn.ping(reconnect=True)
                with self._conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM tickets WHERE channel_id=%s", (channel_id,))
                    return cursor.fetchone()
            except Exception:
                return None

        return await asyncio.to_thread(_sync_get)
