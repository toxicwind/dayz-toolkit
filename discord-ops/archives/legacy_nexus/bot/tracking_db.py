import sqlite3
import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = "player_tracker.db"):
        self.db_path = db_path
        self.init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database schema."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Players table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    steam_id TEXT PRIMARY KEY,
                    real_name TEXT,
                    fake_name TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # Sessions table (history of logins)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    server_name TEXT,
                    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
                )
            ''')
            conn.commit()


    def update_player(self, steam_id: str, real_name: str):
        """Update or insert a player record."""
        with self._connect() as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now()
            
            # Check if player exists
            cursor.execute('SELECT * FROM players WHERE steam_id = ?', (steam_id,))
            player = cursor.fetchone()
            
            if player:
                cursor.execute('''
                    UPDATE players 
                    SET real_name = ?, last_seen = ? 
                    WHERE steam_id = ?
                ''', (real_name, now, steam_id))
            else:
                cursor.execute('''
                    INSERT INTO players (steam_id, real_name, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                ''', (steam_id, real_name, now, now))
            conn.commit()

    def set_alias(self, steam_id: str, fake_name: str):
        """Set a fake name (alias) for a player."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players 
                SET fake_name = ? 
                WHERE steam_id = ?
            ''', (fake_name, steam_id))
            conn.commit()

    def get_player(self, steam_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM players WHERE steam_id = ?', (steam_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_players(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM players ORDER BY last_seen DESC')
            return [dict(row) for row in cursor.fetchall()]

    def log_session(self, steam_id: str, server_name: str = "DayZ Server"):
        """Log a session start for a player."""
        with self._connect() as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now()
            cursor.execute('''
                INSERT INTO sessions (steam_id, start_time, server_name)
                VALUES (?, ?, ?)
            ''', (steam_id, now, server_name))
            conn.commit()

    def get_player_stats(self, steam_id: str) -> Dict[str, Any]:
        """Get aggregated stats for a player"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Get session count and total playtime
            cursor.execute('''
                SELECT 
                    COUNT(*) as session_count,
                    SUM(CAST((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 AS REAL)) as playtime_hours
                FROM sessions
                WHERE steam_id = ?
            ''', (steam_id,))
            
            row = cursor.fetchone()
            
            return {
                'kills': 0,  # TODO: Parse from ADM logs
                'deaths': 0,  # TODO: Parse from ADM logs
                'playtime_hours': round(row['playtime_hours'] or 0, 1),
                'session_count': row['session_count'] or 0,
                'longest_survival_hours': 0,  # TODO: Calculate from sessions
                'favorite_weapon': 'Unknown',  # TODO: Parse from logs
                'preferred_zone': 'Unknown'  # TODO: Parse from position logs
            }
