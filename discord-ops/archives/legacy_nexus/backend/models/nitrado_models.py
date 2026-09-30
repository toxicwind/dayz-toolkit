"""
Pydantic models for Nitrado API
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class HealthMetrics(BaseModel):
    timestamp: str
    status: str
    cpu_usage: float
    ram_usage: float
    player_count: int
    is_healthy: bool
    alerts: List[str]


class HealthSummary(BaseModel):
    status: str
    metrics: HealthMetrics
    crash_count: int
    history_size: int


class BackupInfo(BaseModel):
    id: str
    name: str
    timestamp: str
    size_mb: float
    restorable: bool


class PlayerSessionInfo(BaseModel):
    player_id: str
    player_name: str
    join_time: str
    playtime_minutes: int
    kills: int = 0
    deaths: int = 0
    status: str = "online"


class ResourceDataPoint(BaseModel):
    timestamp: str
    cpu: float
    ram: float


class SettingsSnapshotInfo(BaseModel):
    id: int
    name: str
    created_at: str


class ServerStatusInfo(BaseModel):
    status: str
    players: int
    max_players: int = 60
    game: str = "DayZ"
