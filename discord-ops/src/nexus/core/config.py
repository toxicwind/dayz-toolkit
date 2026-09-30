import os
import yaml
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

log = logging.getLogger("mildlyawesome.config")

class DiscordSettings(BaseModel):
    token: str = ""
    guild_id: int = 0
    status_channel_id: int = 0
    admin_channel_id: int = 0
    query_channel_id: int = 0
    killfeed_channel_id: int = 0
    changefeed_channel_id: int = 0
    stat_channels_json: str = ""
    use_presence: bool = True

class NitradoSettings(BaseModel):
    api_token: str = ""
    service_id: int = 0
    email: Optional[str] = None

class MySQLSettings(BaseModel):
    host: str = "mysql"
    port: int = 3306
    user: str = "dayz"
    password: str = ""
    database: str = "dayz_ops"

class MildlyAwesomeSettings(BaseModel):
    org_id: str = "ezstreet"
    server_name: str = "DayZ Server"
    platform: str = "pc"
    
    discord: DiscordSettings = Field(default_factory=DiscordSettings)
    nitrado: NitradoSettings = Field(default_factory=NitradoSettings)
    bot_mysql: MySQLSettings = Field(default_factory=MySQLSettings)
    
    # Paths & Flags
    disable_ftp_push: bool = True
    enable_selfplay: bool = True
    state_dir: str = "./state/ezstreet"
    
    # Legacy compatibility property accessors
    @property
    def discord_token(self) -> str: return self.discord.token
    @property
    def nitrado_token(self) -> str: return self.nitrado.api_token
    @property
    def nitrado_service_id(self) -> int: return self.nitrado.service_id

# Alias for backward compatibility
Settings = MildlyAwesomeSettings

def load_settings():
    service = os.getenv("CONFIG_SERVICE", "ezstreet")
    # repo_root is 4 levels up from src/mildlyawesome/core/config.py
    repo_root = Path(__file__).parent.parent.parent.parent
    
    # Priority: global.yaml -> teams/{service}.yaml -> Env Overrides
    global_path = repo_root / "config/global.yaml"
    team_path = repo_root / f"config/teams/{service}.yaml"
    
    data = {}
    if global_path.exists():
        with open(global_path) as f:
            data = yaml.safe_load(f) or {}
    
    if team_path.exists():
        with open(team_path) as f:
            team_data = yaml.safe_load(f) or {}
            # Deep merge logic for nested dicts
            for k, v in team_data.items():
                if isinstance(v, dict) and k in data:
                    data[k].update(v)
                else:
                    data[k] = v
    
    # Final Env Injection (Service-Prefixed)
    pfx = f"{service.upper()}_"
    # Special cases for root-level envs
    if os.getenv("DISABLE_FTP_PUSH"):
        data["disable_ftp_push"] = os.getenv("DISABLE_FTP_PUSH") == "1"
    
    # Pydantic will handle the rest of the mapping
    try:
        settings = MildlyAwesomeSettings(**data)
        # Force Env Overrides for sensitive tokens if found
        if os.getenv(f"{pfx}DISCORD_TOKEN"):
            settings.discord.token = os.getenv(f"{pfx}DISCORD_TOKEN")
        if os.getenv(f"{pfx}NITRADO_TOKEN"):
            settings.nitrado.api_token = os.getenv(f"{pfx}NITRADO_TOKEN")
            
        log.info(f"✅ MildlyAwesome Settings Loaded: {settings.org_id} (Service: {settings.nitrado.service_id})")
        return settings
    except Exception as e:
        log.error(f"❌ Failed to parse settings: {e}")
        return MildlyAwesomeSettings()

def get_settings():
    return load_settings()
