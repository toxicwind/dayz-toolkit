import logging
import asyncio
from datetime import datetime, timedelta, date
from typing import Optional, Dict
from dataclasses import dataclass

import discord
from discord.ext import commands

from .database import Database

log = logging.getLogger("dayz-discord-ops.engagement")

@dataclass
class UserEngagement:
    user_id: str
    current_streak: int
    best_streak: int
    last_activity: date
    total_xp: int
    level: int
    messages_sent: int
    voice_minutes: int

class EngagementManager:
    """
    Manages user engagement features: Daily Streaks, XP, Leveling, Activity Rewards.
    Implements mobile app psychology for retention.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()
        
        # XP thresholds for leveling
        self.xp_per_level = 1000  # Base XP needed for level 2
        self.xp_multiplier = 1.5  # Each level requires 1.5x more XP
        
        # Reward amounts
        self.xp_per_message = 5
        self.xp_per_voice_minute = 10
        self.xp_per_kill = 50
        
        self.streak_rewards = {
            7: 100,    # 7 days = 100 coins
            30: 500,   # 30 days = 500 coins
            100: 2000  # 100 days = 2000 coins
        }
        
    def _init_schema(self):
        """Initialize engagement database tables"""
        if not self.db._conn:
            return
            
        sql = """
        CREATE TABLE IF NOT EXISTS user_engagement (
            user_id VARCHAR(50) PRIMARY KEY,
            current_streak INT DEFAULT 0,
            best_streak INT DEFAULT 0,
            last_activity DATE,
            total_xp BIGINT DEFAULT 0,
            level INT DEFAULT 1,
            messages_sent INT DEFAULT 0,
            voice_minutes INT DEFAULT 0,
            first_message_today BOOLEAN DEFAULT FALSE,
            last_daily_reset DATE,
            INDEX idx_level (level),
            INDEX idx_xp (total_xp)
        );
        """
        
        try:
            with self.db._conn.cursor() as cursor:
                cursor.execute(sql)
            log.info("Engagement schema initialized")
        except Exception as e:
            log.error(f"Failed to init engagement schema: {e}")
            
    async def track_message(self, user_id: str) -> Dict:
        """
        Track a user message and award XP.
        Returns dict with: xp_gained, level_up (bool), streak_updated (bool), bonus_coins
        """
        result = {
            'xp_gained': self.xp_per_message,
            'level_up': False,
            'new_level': 1,
            'streak_updated': False,
            'new_streak': 0,
            'bonus_coins': 0,
            'first_message_bonus': False
        }
        
        try:
            engagement = await self._get_or_create_user(user_id)
            today = date.today()
            
            # Check for "First Message of the Day" bonus
            if engagement.last_activity != today:
                result['first_message_bonus'] = True
                result['bonus_coins'] += 25
                
                # Update streak
                if engagement.last_activity == today - timedelta(days=1):
                    # Consecutive day
                    engagement.current_streak += 1
                elif engagement.last_activity and (today - engagement.last_activity).days > 1:
                    # Streak broken (but allow 28-hour grace period)
                    hours_diff = (datetime.now() - datetime.combine(engagement.last_activity, datetime.min.time())).total_seconds() / 3600
                    if hours_diff > 28:
                        engagement.current_streak = 1
                    else:
                        engagement.current_streak += 1
                else:
                    engagement.current_streak = 1
                    
                if engagement.current_streak > engagement.best_streak:
                    engagement.best_streak = engagement.current_streak
                    
                result['streak_updated'] = True
                result['new_streak'] = engagement.current_streak
                
                # Check for streak milestone rewards
                if engagement.current_streak in self.streak_rewards:
                    milestone_coins = self.streak_rewards[engagement.current_streak]
                    result['bonus_coins'] += milestone_coins
                    result['streak_milestone'] = engagement.current_streak
                    
            # Award XP
            engagement.total_xp += self.xp_per_message
            engagement.messages_sent += 1
            engagement.last_activity = today
            
            # Check for level up
            new_level = self._calculate_level(engagement.total_xp)
            if new_level > engagement.level:
                result['level_up'] = True
                result['new_level'] = new_level
                engagement.level = new_level
            else:
                result['new_level'] = engagement.level
                
            # Save to DB
            await self._save_user(engagement)
            
        except Exception as e:
            log.exception(f"Error tracking message for {user_id}: {e}")
            
        return result
        
    async def track_voice_time(self, user_id: str, minutes: int):
        """Track voice chat time and award XP"""
        try:
            engagement = await self._get_or_create_user(user_id)
            xp_gain = minutes * self.xp_per_voice_minute
            engagement.total_xp += xp_gain
            engagement.voice_minutes += minutes
            
            new_level = self._calculate_level(engagement.total_xp)
            if new_level > engagement.level:
                engagement.level = new_level
                
            await self._save_user(engagement)
            
        except Exception as e:
            log.exception(f"Error tracking voice for {user_id}: {e}")
            
    async def track_kill(self, user_id: str):
        """Award XP for a confirmed kill"""
        try:
            engagement = await self._get_or_create_user(user_id)
            engagement.total_xp += self.xp_per_kill
            
            new_level = self._calculate_level(engagement.total_xp)
            if new_level > engagement.level:
                engagement.level = new_level
                
            await self._save_user(engagement)
            
        except Exception as e:
            log.exception(f"Error tracking kill for {user_id}: {e}")
            
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level from total XP"""
        level = 1
        xp_needed = self.xp_per_level
        remaining_xp = total_xp
        
        while remaining_xp >= xp_needed:
            remaining_xp -= xp_needed
            level += 1
            xp_needed = int(xp_needed * self.xp_multiplier)
            
        return level
        
    async def _get_or_create_user(self, user_id: str) -> UserEngagement:
        """Get user engagement data or create new record"""
        if not self.db._conn:
            return UserEngagement(
                user_id=user_id,
                current_streak=0,
                best_streak=0,
                last_activity=None,
                total_xp=0,
                level=1,
                messages_sent=0,
                voice_minutes=0
            )
            
        try:
            with self.db._conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM user_engagement WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return UserEngagement(
                        user_id=row['user_id'],
                        current_streak=row['current_streak'],
                        best_streak=row['best_streak'],
                        last_activity=row['last_activity'],
                        total_xp=row['total_xp'],
                        level=row['level'],
                        messages_sent=row['messages_sent'],
                        voice_minutes=row['voice_minutes']
                    )
                else:
                    # Create new user
                    return UserEngagement(
                        user_id=user_id,
                        current_streak=0,
                        best_streak=0,
                        last_activity=None,
                        total_xp=0,
                        level=1,
                        messages_sent=0,
                        voice_minutes=0
                    )
        except Exception as e:
            log.error(f"Error getting user engagement: {e}")
            return UserEngagement(
                user_id=user_id,
                current_streak=0,
                best_streak=0,
                last_activity=None,
                total_xp=0,
                level=1,
                messages_sent=0,
                voice_minutes=0
            )
            
    async def _save_user(self, engagement: UserEngagement):
        """Save user engagement data to database"""
        if not self.db._conn:
            return
            
        try:
            with self.db._conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_engagement 
                    (user_id, current_streak, best_streak, last_activity, total_xp, level, messages_sent, voice_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        current_streak = VALUES(current_streak),
                        best_streak = VALUES(best_streak),
                        last_activity = VALUES(last_activity),
                        total_xp = VALUES(total_xp),
                        level = VALUES(level),
                        messages_sent = VALUES(messages_sent),
                        voice_minutes = VALUES(voice_minutes)
                """, (
                    engagement.user_id,
                    engagement.current_streak,
                    engagement.best_streak,
                    engagement.last_activity,
                    engagement.total_xp,
                    engagement.level,
                    engagement.messages_sent,
                    engagement.voice_minutes
                ))
        except Exception as e:
            log.exception(f"Error saving user engagement: {e}")

# Global instance
_engagement_manager: Optional[EngagementManager] = None

def get_engagement_manager() -> Optional[EngagementManager]:
    return _engagement_manager

def init_engagement_manager(db: Database):
    global _engagement_manager
    _engagement_manager = EngagementManager(db)
    return _engagement_manager
