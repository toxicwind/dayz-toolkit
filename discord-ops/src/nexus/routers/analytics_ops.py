
from fastapi import APIRouter
import logging
import asyncio
from datetime import datetime
from pydantic import BaseModel
from src.mildlyawesome.globals import get_bot
from src.mildlyawesome.config import load_settings
from src.mildlyawesome.database import Database, get_db_connection

router = APIRouter(tags=["Analytics Ops"])
log = logging.getLogger("mildlyawesome.api.analytics")

@router.get("/analytics/summary")
async def get_analytics_summary():
    """Expose player/mission summary from analytics.py"""
    try:
        from src.mildlyawesome.analytics import get_summary
        return await get_summary()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/analytics/players/active")
async def get_active_players():
    """Expose active player list from analytics.py"""
    try:
        from src.mildlyawesome.analytics import get_active_players_list
        return await get_active_players_list()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/stats/overview")
async def get_stats_overview(org_id: str = "ezstreet"):
    """Consolidated overview stats for the dashboard cards."""
    settings = load_settings()
    db = Database(settings)
    
    active_players = 0
    max_players = 60
    server_status = "OFFLINE"
    
    bot = get_bot()
    if bot:
        cog = bot.get_cog("StatusCog")
        if cog:
            status = cog.service.get_cached_status()
            if status:
                active_players = status.players
                max_players = status.max_players
                server_status = status.status

    total_profiles = 0
    total_kills = 0
    total_structures = 0
    
    conn = await db.connect()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM player_profiles WHERE org_id=%s", (org_id,))
                total_profiles = cursor.fetchone()["count"]
                
                cursor.execute("SELECT COUNT(*) as count FROM combat_logs WHERE org_id=%s", (org_id,))
                total_kills = cursor.fetchone()["count"]
                
                cursor.execute("SELECT COUNT(*) as count FROM activity_logs WHERE org_id=%s AND type='BUILDING'", (org_id,))
                total_structures = cursor.fetchone()["count"]
        except Exception as e:
            log.error(f"Error fetching stats: {e}")
        finally:
            conn.close()
            
    return {
        "active_players": active_players,
        "max_players": max_players,
        "server_status": server_status,
        "total_profiles": total_profiles,
        "total_kills": total_kills,
        "total_structures": total_structures,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/stats/trends")
async def get_stats_trends(org_id: str = "ezstreet", window_hours: int = 24):
    """Historical data for charts/graphs."""
    settings = load_settings()
    db = Database(settings)
    
    trends = []
    conn = await db.connect()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT timestamp, player_count, max_players 
                       FROM player_stats 
                       WHERE org_id=%s AND timestamp > DATE_SUB(NOW(), INTERVAL %s HOUR)
                       ORDER BY timestamp ASC""",
                    (org_id, window_hours)
                )
                trends = cursor.fetchall()
        except Exception as e:
            log.error(f"Error fetching trends: {e}")
        finally:
            conn.close()
            
    return {
        "trends": [
            {
                "timestamp": t["timestamp"].isoformat() if isinstance(t["timestamp"], datetime) else t["timestamp"],
                "player_count": t["player_count"],
                "max_players": t["max_players"]
            } 
            for t in trends
        ],
        "window_hours": window_hours
    }

@router.get("/stats/history")
async def get_stats_history():
    """Get historical server stats for charts (Legacy compat)"""
    settings = load_settings()
    stats = []

    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"stats": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT timestamp, player_count, max_players
                    FROM server_stats
                    WHERE timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    ORDER BY timestamp ASC
                    """
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        for row in rows:
            ts = row[0]
            stats.append(
                {
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else None,
                    "player_count": row[1],
                    "max_players": row[2],
                }
            )
        conn.close()
    except Exception as e:
        log.error(f"Failed to fetch stats history: {e}")

    return {"stats": stats}

@router.get("/killfeed")
async def get_killfeed(limit: int = 50):
    """Real-time combat log exposure."""
    settings = load_settings()
    conn = await get_db_connection(settings)
    if not conn:
        return {"kills": []}

    try:
        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM combat_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        return {"kills": rows}
    except Exception as e:
        log.error(f"Failed to fetch killfeed: {e}")
        return {"kills": []}
    finally:
        conn.close()

@router.get("/analytics/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Top players by kills and KD ratio"""
    settings = load_settings()
    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"players": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT last_known_name as name, player_id, kills, deaths,
                           (kills / NULLIF(deaths, 0)) as kd
                    FROM player_profiles
                    ORDER BY kills DESC, kd DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        conn.close()
        return {"players": rows}
    except Exception as e:
        log.error(f"Leaderboard failed: {e}")
        return {"players": [], "error": str(e)}

@router.get("/analytics/hotzones")
async def get_hotzones():
    """Kill heatmap data (clustered locations)."""
    settings = load_settings()
    try:
        conn = await get_db_connection(settings)
        if not conn:
            return {"hotzones": []}

        def _fetch():
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ROUND(pos_x, -2) as x, ROUND(pos_z, -2) as z, COUNT(*) as weight
                    FROM combat_logs
                    WHERE pos_x IS NOT NULL AND pos_z IS NOT NULL
                    GROUP BY x, z
                    HAVING weight >= 1
                    LIMIT 200
                    """
                )
                return cursor.fetchall()

        rows = await asyncio.to_thread(_fetch)
        conn.close()
        return {"hotzones": rows}
    except Exception as e:
        log.error(f"Hotzones failed: {e}")
        return {"hotzones": [], "error": str(e)}
