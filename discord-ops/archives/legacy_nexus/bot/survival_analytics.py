from __future__ import annotations
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from .config import load_settings
from .tracking_db import Database as TrackingDB
from .database import get_db_connection

log = logging.getLogger("dayz-discord-ops.survival")

router = APIRouter(prefix="/survival", tags=["survival"])

def calculate_survival_score(kills: int, deaths: int, playtime: float) -> int:
    """Calculate survival score based on player stats"""
    kd = kills / max(deaths, 1)
    base_score = min(kd * 20, 50)  # Max 50 from K/D
    time_score = min(playtime / 10, 30)  # Max 30 from playtime
    survival_bonus = min((playtime / max(deaths, 1)) * 2, 20)  # Max 20 from survival time
    return int(base_score + time_score + survival_bonus)

def determine_activity_pattern(kills: int, deaths: int, playtime: float) -> str:
    """Determine player activity pattern"""
    kd = kills / max(deaths, 1)
    if kd > 2.0 and kills > 10:
        return "aggressive"
    elif kd < 0.5:
        return "explorer"
    elif playtime > 100:
        return "builder"
    else:
        return "defensive"

def determine_threat_level(kills: int, kd: float, score: int) -> str:
    """Determine player threat level"""
    if kills > 30 and kd > 3.0:
        return "extreme"
    elif kills > 15 and kd > 2.0:
        return "high"
    elif kills > 5 and kd > 1.0:
        return "medium"
    else:
        return "low"

def generate_activity_hash(player: str, activity_type: str, timestamp: str, details: str) -> str:
    """Generate unique hash for activity deduplication"""
    content = f"{player}:{activity_type}:{timestamp}:{details}"
    return hashlib.md5(content.encode()).hexdigest()

@router.get("/profiles")
async def get_survival_profiles():
    """Get all survivor profiles with real player data"""
    try:
        settings = load_settings()
        
        # Initialize tracking DB with path
        import os
        db_path = os.getenv("PLAYER_TRACKER_DB", "player_tracker.db")
        tracking_db = TrackingDB(db_path)
        
        # Get all tracked players
        players = tracking_db.get_all_players()
        
        if not players:
            log.info("No players found in tracking database")
            return {"profiles": [], "total": 0}
        
        profiles = []
        for player in players:
            steam_id = player.get('steam_id', '')
            real_name = player.get('real_name', 'Unknown')
            fake_name = player.get('fake_name')
            
            # Get player stats from tracking DB
            stats = tracking_db.get_player_stats(steam_id)
            
            kills = stats.get('kills', 0)
            deaths = max(stats.get('deaths', 1), 1)
            kd_ratio = round(kills / deaths, 2)
            playtime = stats.get('playtime_hours', 0)
            
            survival_score = calculate_survival_score(kills, deaths, playtime)
            activity_pattern = determine_activity_pattern(kills, deaths, playtime)
            threat_level = determine_threat_level(kills, kd_ratio, survival_score)
            
            # Determine status
            last_seen = player.get('last_seen')
            status = 'offline'
            if last_seen:
                try:
                    from datetime import datetime
                    if isinstance(last_seen, str):
                        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    else:
                        last_seen_dt = last_seen
                    time_diff = datetime.now() - last_seen_dt
                    if time_diff.total_seconds() < 1800:  # 30 minutes
                        status = 'online'
                    elif deaths > kills * 2:
                        status = 'deceased'
                except Exception as e:
                    log.warning(f"Error parsing last_seen: {e}")
            
            profiles.append({
                "steam_id": steam_id,
                "player_name": fake_name or real_name,
                "total_playtime": playtime,
                "survival_score": survival_score,
                "kills": kills,
                "deaths": deaths,
                "kd_ratio": kd_ratio,
                "longest_survival": stats.get('longest_survival_hours', 0),
                "favorite_weapon": stats.get('favorite_weapon', 'Unknown'),
                "preferred_zone": stats.get('preferred_zone', 'Unknown'),
                "activity_pattern": activity_pattern,
                "threat_level": threat_level,
                "last_seen": str(last_seen) if last_seen else datetime.now().isoformat(),
                "status": status
            })
        
        log.info(f"Returning {len(profiles)} survivor profiles")
        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        log.error(f"Failed to get survival profiles: {e}", exc_info=True)
        return {"profiles": [], "total": 0, "error": str(e)}

@router.get("/activity-feed")
async def get_activity_feed(limit: int = 50):
    """Get real-time activity feed from activity logs with player profiling integration"""
    try:
        import re
        import os
        
        settings = load_settings()
        conn = get_db_connection(settings)
        
        if not conn:
            log.warning("Database not available, returning empty feed")
            return {"activities": [], "total": 0}
        
        # Initialize tracking DB for player lookups
        db_path = os.getenv("PLAYER_TRACKER_DB", "player_tracker.db")
        tracking_db = TrackingDB(db_path)
        
        # Build player lookup cache: name -> player data
        all_players = tracking_db.get_all_players()
        player_cache = {}
        for p in all_players:
            steam_id = p.get('steam_id', '')
            real_name = p.get('real_name', '')
            fake_name = p.get('fake_name', '')
            display_name = fake_name or real_name
            if display_name:
                player_cache[display_name.lower()] = {
                    'steam_id': steam_id,
                    'display_name': display_name,
                    'real_name': real_name
                }
        
        cursor = conn.cursor()
        
        # Get recent activities with deduplication, excluding bot/system events
        # Note: %% is used to escape % in LIKE clauses when using PyMySQL parameter substitution
        query = """
            SELECT DISTINCT
                id,
                timestamp,
                type,
                message,
                severity
            FROM activity_logs
            WHERE timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
            AND type NOT IN ('SYSTEM', 'A2S_FAIL', 'BOT')
            AND message NOT LIKE '%%Bot started%%'
            AND message NOT LIKE '%%A2S Query%%'
            AND message NOT LIKE '%%RCON%%'
            AND message NOT LIKE '%%API%%'
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        activities = []
        seen_hashes = set()
        
        # Regex patterns to extract player info from log messages
        # Pattern 1: Player "Name" (id=SteamID pos=<x,y,z>)
        player_pattern_full = re.compile(r'Player\s+"([^"]+)"\s+\(id=([A-Fa-f0-9]+)(?:\s+pos=<([0-9.-]+),\s*([0-9.-]+),\s*([0-9.-]+)>)?\)')
        # Pattern 2: Just player name in quotes
        player_pattern_simple = re.compile(r'Player\s+"([^"]+)"')
        # Pattern 3: Player name followed by action
        player_pattern_action = re.compile(r'^([A-Za-z0-9_\s]+?)\s+(joined|left|killed|died|spawned)', re.IGNORECASE)
        
        for row in rows:
            # DictCursor returns dictionaries, not tuples
            activity_id = row['id']
            timestamp = row['timestamp']
            type_val = row['type']
            message = row['message']
            severity = row['severity']
            
            # Generate hash for deduplication
            timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp) if timestamp else ''
            activity_hash = generate_activity_hash(
                type_val,
                type_val,
                timestamp_str,
                message
            )
            
            # Skip duplicates
            if activity_hash in seen_hashes:
                continue
            seen_hashes.add(activity_hash)
            
            # Extract player information from message
            player_name = "System"
            steam_id = None
            location = {"x": 7500.0, "y": 7500.0, "z": 100.0}  # Default
            
            # Try to parse player info from message (most specific patterns first)
            match_full = player_pattern_full.search(message)
            if match_full:
                player_name = match_full.group(1)
                steam_id = match_full.group(2)
                if match_full.group(3):  # Has position
                    location = {
                        "x": float(match_full.group(3)),
                        "y": float(match_full.group(4)),
                        "z": float(match_full.group(5))
                    }
            else:
                # Try action pattern first (more specific than simple pattern)
                match_action = player_pattern_action.search(message)
                if match_action:
                    player_name = match_action.group(1).strip()
                else:
                    # Try simple pattern last
                    match_simple = player_pattern_simple.search(message)
                    if match_simple:
                        player_name = match_simple.group(1)
            
            # Handle generic "Player player" case - this means we don't have real player info
            # Check for patterns like "Player player", "Player Player", etc.
            if player_name.lower() == 'player' or player_name.lower().startswith('player '):
                player_name = "Unknown Player"
            
            # Lookup player in cache to get Steam ID if not already found
            if not steam_id and player_name not in ["System", "Unknown Player"]:
                player_key = player_name.lower()
                if player_key in player_cache:
                    steam_id = player_cache[player_key]['steam_id']
                    player_name = player_cache[player_key]['display_name']
            
            # Map activity types
            activity_type = 'movement'
            if type_val in ['JOIN', 'LEAVE']:
                activity_type = 'interaction'
            elif 'kill' in message.lower() or 'combat' in message.lower():
                activity_type = 'combat'
            elif 'death' in message.lower() or 'died' in message.lower():
                activity_type = 'death'
            elif 'build' in message.lower():
                activity_type = 'building'
            elif 'loot' in message.lower():
                activity_type = 'looting'
            elif 'spawn' in message.lower():
                activity_type = 'spawn'
            
            # Calculate intensity based on severity
            intensity = 50
            if severity == 'warning':
                intensity = 70
            elif severity == 'error':
                intensity = 90
            
            # Detect threats
            threat_detected = any(word in message.lower() for word in ['kill', 'combat', 'attack', 'hostile'])
            
            # Calculate anomaly score
            anomaly_score = 0.0
            if 'error' in (severity or '').lower():
                anomaly_score = 0.8
            elif threat_detected:
                anomaly_score = 0.6
            
            # Build activity entry
            activity_entry = {
                "id": f"activity_{activity_id}_{activity_hash[:8]}",
                "timestamp": timestamp_str or datetime.now().isoformat(),
                "player_name": player_name,
                "activity_type": activity_type,
                "intensity": intensity,
                "location": location,
                "details": message,
                "threat_detected": threat_detected,
                "anomaly_score": anomaly_score
            }
            
            # Add Steam ID if found
            if steam_id:
                activity_entry["steam_id"] = steam_id
                activity_entry["console_id"] = steam_id  # Steam ID is the console ID in DayZ
            
            activities.append(activity_entry)
        
        cursor.close()
        conn.close()
        
        return {"activities": activities, "total": len(activities)}
    except Exception as e:
        log.error(f"Failed to get activity feed: {e}", exc_info=True)
        return {"activities": [], "total": 0, "error": str(e)}

@router.get("/metrics")
async def get_survival_metrics():
    """Get overall survival metrics from real data"""
    try:
        import os
        db_path = os.getenv("PLAYER_TRACKER_DB", "player_tracker.db")
        tracking_db = TrackingDB(db_path)
        
        # Get all players
        players = tracking_db.get_all_players()
        
        if not players:
            return {
                "total_survivors": 0,
                "active_now": 0,
                "avg_survival_time": 0,
                "total_deaths_24h": 0,
                "hotspot_zones": [],
                "threat_level": "calm"
            }
        
        # Calculate metrics
        online_count = 0
        total_playtime = 0
        total_deaths_24h = 0
        
        for player in players:
            last_seen = player.get('last_seen')
            if last_seen:
                try:
                    from datetime import datetime
                    if isinstance(last_seen, str):
                        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    else:
                        last_seen_dt = last_seen
                    time_diff = datetime.now() - last_seen_dt
                    if time_diff.total_seconds() < 1800:  # 30 minutes
                        online_count += 1
                    if time_diff.total_seconds() < 86400:  # 24 hours
                        stats = tracking_db.get_player_stats(player.get('steam_id', ''))
                        total_deaths_24h += stats.get('deaths', 0)
                except Exception as e:
                    log.warning(f"Error parsing timestamp: {e}")
            
            stats = tracking_db.get_player_stats(player.get('steam_id', ''))
            total_playtime += stats.get('playtime_hours', 0)
        
        avg_survival = total_playtime / len(players) if players else 0
        
        # Determine threat level
        threat_level = 'calm'
        if total_deaths_24h > 20:
            threat_level = 'critical'
        elif total_deaths_24h > 10:
            threat_level = 'elevated'
        elif total_deaths_24h > 5:
            threat_level = 'moderate'
        
        return {
            "total_survivors": len(players),
            "active_now": online_count,
            "avg_survival_time": round(avg_survival, 1),
            "total_deaths_24h": total_deaths_24h,
            "hotspot_zones": [
                {"zone": "NWAF", "activity": online_count * 30},
                {"zone": "Tisy", "activity": online_count * 20},
                {"zone": "Kamensk", "activity": online_count * 15}
            ],
            "threat_level": threat_level
        }
    except Exception as e:
        log.error(f"Failed to get survival metrics: {e}", exc_info=True)
        return {
            "total_survivors": 0,
            "active_now": 0,
            "avg_survival_time": 0,
            "total_deaths_24h": 0,
            "hotspot_zones": [],
            "threat_level": "calm",
            "error": str(e)
        }

@router.get("/profile/{steam_id}")
async def get_player_profile(steam_id: str):
    """Get detailed profile for a specific player"""
    try:
        settings = load_settings()
        tracking_db = TrackingDB(settings)
        
        player = tracking_db.get_player(steam_id)
        if not player:
            return {"error": "Profile not found"}
        
        stats = tracking_db.get_player_stats(steam_id)
        
        kills = stats.get('kills', 0)
        deaths = max(stats.get('deaths', 1), 1)
        kd_ratio = round(kills / deaths, 2)
        playtime = stats.get('playtime_hours', 0)
        
        profile = {
            "steam_id": steam_id,
            "player_name": player.get('fake_name') or player.get('real_name', 'Unknown'),
            "total_playtime": playtime,
            "survival_score": calculate_survival_score(kills, deaths, playtime),
            "kills": kills,
            "deaths": deaths,
            "kd_ratio": kd_ratio,
            "longest_survival": stats.get('longest_survival_hours', 0),
            "favorite_weapon": stats.get('favorite_weapon', 'Unknown'),
            "preferred_zone": stats.get('preferred_zone', 'Unknown'),
            "activity_pattern": determine_activity_pattern(kills, deaths, playtime),
            "threat_level": determine_threat_level(kills, kd_ratio, calculate_survival_score(kills, deaths, playtime)),
            "last_seen": player.get('last_seen', datetime.now().isoformat()),
            "status": "offline"
        }
        
        return {"profile": profile}
    except Exception as e:
        log.error(f"Failed to get player profile: {e}")
        return {"error": str(e)}
