from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

def _read_secret_file(path: str) -> Optional[str]:
    try:
        p = Path(path)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return None

def env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v

def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    return int(raw)

def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    return float(raw)

def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")

def secret_or_env(name: str) -> Optional[str]:
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        v = _read_secret_file(file_path)
        if v:
            return v
    return os.getenv(name)

@dataclass(frozen=True)
class Settings:
    discord_token: str
    discord_guild_id: int
    discord_admin_role_ids: tuple[int, ...]
    use_presence: bool

    dayz_host: str
    dayz_query_port: int
    dayz_rcon_port: int
    dayz_rcon_password: str
    a2s_timeout: float
    a2s_retries: int
    a2s_retry_backoff: float
    a2s_cache_ttl: int

    stat_channels_json: str | None
    metrics_enable: bool
    metrics_port: int

    ftp_host: str | None
    ftp_port: int
    ftp_user: str | None
    ftp_pass: str | None

    mysql_host: str | None
    mysql_port: int
    mysql_user: str | None
    mysql_pass: str | None
    mysql_db: str | None

def load_settings() -> Settings:
    token = secret_or_env("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN (or DISCORD_BOT_TOKEN_FILE)")
    guild_id = int(env_required("DISCORD_GUILD_ID"))

    roles_raw = env_required("DISCORD_ADMIN_ROLE_IDS")
    role_ids = tuple(int(x.strip()) for x in roles_raw.split(",") if x.strip())

    rcon_pass = secret_or_env("DAYZ_RCON_PASSWORD")
    if not rcon_pass:
        raise RuntimeError("Missing DAYZ_RCON_PASSWORD (or DAYZ_RCON_PASSWORD_FILE)")

    return Settings(
        discord_token=token,
        discord_guild_id=guild_id,
        discord_admin_role_ids=role_ids,
        use_presence=env_bool("DISCORD_USE_PRESENCE", False),
        dayz_host=env_required("DAYZ_HOST"),
        dayz_query_port=env_int("DAYZ_QUERY_PORT", 27016),
        dayz_rcon_port=env_int("DAYZ_RCON_PORT", 2305),
        dayz_rcon_password=rcon_pass,
        a2s_timeout=env_float("A2S_TIMEOUT", 2.0),
        a2s_retries=env_int("A2S_RETRIES", 2),
        a2s_retry_backoff=env_float("A2S_RETRY_BACKOFF", 1.5),
        a2s_cache_ttl=env_int("A2S_CACHE_TTL_SECONDS", 300),
        stat_channels_json=os.getenv("STAT_CHANNELS_JSON"),
        metrics_enable=env_bool("METRICS_ENABLE", False),
        metrics_port=env_int("METRICS_PORT", 9108),
        ftp_host=os.getenv("DAYZ_FTP_HOST"),
        ftp_port=env_int("DAYZ_FTP_PORT", 21),
        ftp_user=os.getenv("DAYZ_FTP_USER"),
        ftp_pass=secret_or_env("DAYZ_FTP_PASS"),
        mysql_host=os.getenv("DAYZ_MYSQL_HOST"),
        mysql_port=env_int("DAYZ_MYSQL_PORT", 3306),
        mysql_user=os.getenv("DAYZ_MYSQL_USER"),
        mysql_pass=secret_or_env("DAYZ_MYSQL_PASS"),
        mysql_db=os.getenv("DAYZ_MYSQL_DB"),
    )
