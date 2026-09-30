from __future__ import annotations
import logging
import time
import pymysql
from pymysql.cursors import DictCursor
from .config import Settings

log = logging.getLogger("dayz-discord-ops.db")

class Database:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._conn = None

    def connect(self):
        if not self._settings.mysql_host:
            log.warning("MySQL host not configured. Database logging disabled.")
            return None
        
        try:
            self._conn = pymysql.connect(
                host=self._settings.mysql_host,
                port=self._settings.mysql_port,
                user=self._settings.mysql_user,
                password=self._settings.mysql_pass,
                database=self._settings.mysql_db,
                cursorclass=DictCursor,
                autocommit=True
            )
            log.info("Connected to MySQL database")
            self._init_schema()
            return self._conn
        except Exception as e:
            log.error(f"Failed to connect to MySQL: {e}")
            return None

    def _init_schema(self):
        if not self._conn:
            return
        
        schema = """
        CREATE TABLE IF NOT EXISTS player_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            player_count INT NOT NULL,
            max_players INT NOT NULL,
            INDEX idx_timestamp (timestamp)
        );
        """
        try:
            with self._conn.cursor() as cursor:
                cursor.execute(schema)
            log.info("Database schema initialized")
        except Exception as e:
            log.error(f"Failed to initialize schema: {e}")

    def log_stats(self, players: int, max_players: int):
        if not self._conn:
            # Try to reconnect if connection was lost or never established
            if not self.connect():
                return
        
        try:
            # Check connection
            self._conn.ping(reconnect=True)
            
            with self._conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO player_stats (player_count, max_players) VALUES (%s, %s)",
                    (players, max_players)
                )
            log.info(f"Logged stats: {players}/{max_players}")
        except Exception as e:
            log.error(f"Failed to log stats: {e}")
