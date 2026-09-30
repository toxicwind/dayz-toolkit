from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


def _deep_merge(source: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _deep_merge(value, node)
        else:
            destination[key] = value
    return destination


@dataclass
class NitradoSettings:
    api_token: str = ""
    service_id: int = 0
    email: str | None = None
    password: str | None = None


@dataclass
class DiscordLiveUpdateSettings:
    # REQUIRED: set these in env (or your existing config layer)
    STATUS_WEBHOOK_URL: str = os.getenv("STATUS_WEBHOOK_URL", "")
    KILLFEED_WEBHOOK_URL: str = os.getenv("KILLFEED_WEBHOOK_URL", "")
    ADMIN_WEBHOOK_URL: str = os.getenv("ADMIN_WEBHOOK_URL", "")
    LOOT_WEBHOOK_URL: str = os.getenv("LOOT_WEBHOOK_URL", "")

    STATUS_INTERVAL_S: int = int(os.getenv("DISCORD_STATUS_INTERVAL_S", "60"))
    BURST_WINDOW_S: int = int(os.getenv("DISCORD_BURST_WINDOW_S", "3"))
    MAX_QUEUE: int = int(os.getenv("DISCORD_MAX_QUEUE", "500"))

    STATE_PATH: str = os.getenv("DISCORD_LIVE_STATE_PATH", "backend/state/discord_live_state.json")


@dataclass
class DiscordSettings:
    token: str = ""
    guild_id: int = 0
    admin_role_ids: list[int] = field(default_factory=list)
    admin_channel_id: int = 0
    status_channel_id: int = 0
    changefeed_channel_id: int = 0
    killfeed_channel_id: int = 0
    deathfeed_channel_id: int = 0
    # Live update system channels
    server_status_channel_id: int = 0
    admin_log_channel_id: int = 0
    loot_events_channel_id: int = 0
    use_presence: bool = True
    stat_channels_json: str = ""


@dataclass
class MySQLSettings:
    host: str = ""
    port: int = 19102
    user: str = ""
    password: str = ""
    database: str = ""


@dataclass
class Settings:
    nitrado: NitradoSettings = field(default_factory=NitradoSettings)
    discord: DiscordSettings = field(default_factory=DiscordSettings)
    bot_mysql: MySQLSettings = field(default_factory=MySQLSettings)
    nitrado_mysql: MySQLSettings = field(default_factory=MySQLSettings)

    org_id: str = "cluster"
    server_name: str = "DayZ Server"
    platform: str = "pc"

    killfeed_enabled: bool = True

    # Query
    dayz_host: str = ""
    dayz_query_port: int = 2302

    # FTP
    ftp_host: str = ""
    ftp_port: int = 21
    ftp_user: str = ""
    ftp_password: str = ""
    ftp_log_path: str = ""
    ftp_base_path: str = "/"
    ftp_mission_path: str = ""
    state_dir: str = ""
    mission_path: str = ""

    # Metrics
    metrics_enabled: bool = False
    metrics_port: int = 9110
    # A2S Query settings (referenced in src.mildlyawesome.py)
    a2s_timeout: float = 3.0
    a2s_retries: int = 2
    a2s_retry_backoff: float = 1.0
    a2s_cache_ttl: float = 5.0
    a2s_port_offsets: list[int] = field(default_factory=lambda: [0])
    a2s_packet_pad_to: int = 0
    # Paths
    vanilla_path: str = ""
    mission_path: str = ""
    patches_src_dir: str = ""
    ftp_dump_local_path: str = "./staging/ftp_base"
    ftp_ingest_local_path: str = "./staging/ezstreet"

    # Chronos/System Paths
    chronos_root: Path = field(default_factory=Path)
    staging_dir: Path = field(default_factory=Path)
    manifest_path: Path = field(default_factory=Path)
    vscode_settings_path: Path = field(default_factory=Path)
    vscode_extensions_dir: Path = field(default_factory=Path)

    # Legacy compatibility properties
    @property
    def mysql_host(self) -> str:
        return self.bot_mysql.host

    @property
    def mysql_port(self) -> int:
        return self.bot_mysql.port

    def reload(self):
        """Force a reload of the settings from disk."""
        new_settings = load_settings(service=self.org_id)
        # Update current instance attributes
        for key, value in new_settings.__dict__.items():
            setattr(self, key, value)
        log.info(f"🔄 Configuration reloaded for {self.org_id}")

    @property
    def mysql_user(self) -> str:
        return self.bot_mysql.user

    @property
    def mysql_pass(self) -> str:
        return self.bot_mysql.password

    @property
    def mysql_db(self) -> str:
        return self.bot_mysql.database

    @property
    def discord_token(self) -> str:
        return self.discord.token

    @property
    def discord_guild_id(self) -> int:
        return self.discord.guild_id

    @property
    def discord_admin_role_ids(self) -> list[int]:
        return self.discord.admin_role_ids

    @property
    def stat_channels_json(self) -> Any:
        return self.discord.stat_channels_json

    @property
    def killfeed_channel_id(self) -> int | None:
        return self.discord.killfeed_channel_id

    @property
    def restart_channel_id(self) -> int | None:
        return None

    @property
    def changelog_channel_id(self) -> int | None:
        return self.discord.changefeed_channel_id

    @property
    def use_presence(self) -> bool:
        return self.discord.use_presence

    @property
    def nitrado_token(self) -> str:
        return self.nitrado.api_token

    @property
    def nitrado_service_id(self) -> int:
        return self.nitrado.service_id


def load_settings(env: str = "dev", service: str = "ezstreet") -> Settings:
    """YAML-first loader; CONFIG_ENV/CONFIG_SERVICE override defaults. No .env reliance."""

    env = os.getenv("CONFIG_ENV", env)
    service = os.getenv("CONFIG_SERVICE", service)

    # Config is in root/config
    repo_root = Path(__file__).parent.parent.parent
    config_dir = repo_root / "config"

    from .secrets_loader import get_secret


    # Canonical layout as of 2025-12-28:
    #   config/global.yaml           -> shared defaults
    #   config/env/<env>.yaml        -> optional environment overrides
    #   config/teams/<service>.yaml  -> per-team/service config (ezstreet, etc.)
    files = [
        config_dir / "global.yaml",
        config_dir / f"env/{env}.yaml",
        config_dir / f"teams/{service}.yaml",
    ]

    conf_data: dict[str, Any] = {}
    for f in files:
        if f.exists():
            with open(f, encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
                _deep_merge(data, conf_data)

    nit = conf_data.get("nitrado", {})
    disc = conf_data.get("discord", {})
    b_mysql = conf_data.get("bot_mysql", {})
    n_mysql = conf_data.get("nitrado_mysql", {})
    paths_conf = conf_data.get("paths", {})

    # Secrets can be overridden via env; structure stays YAML-driven
    nit_token = os.getenv("EZSTREET_NITRADO_TOKEN", nit.get("api_token", ""))

    env_stat_json = os.getenv("STAT_CHANNELS_JSON")
    stat_channels_val = env_stat_json if env_stat_json is not None else disc.get("stat_channels_json", "")

    ftp_conf = conf_data.get("ftp", {})
    ftp_user = ftp_conf.get("user") or os.getenv("EZSTREET_FTP_USER", "")
    ftp_password = ftp_conf.get("password") or os.getenv("EZSTREET_FTP_PASSWORD", "")
    state_dir = paths_conf.get("state_dir") or f"./state/{service}"

    return Settings(
        nitrado=NitradoSettings(
            api_token=nit_token,
            service_id=int(nit.get("service_id", 0)),
            email=nit.get("email"),
            password=nit.get("password"),
        ),
        discord=DiscordSettings(
            token=get_secret("DISCORD_TOKEN") or get_secret("EZSTREET_DISCORD_TOKEN") or disc.get("token", ""),
            guild_id=int(get_secret("DISCORD_GUILD_ID") or disc.get("guild_id", 0)),
            admin_role_ids=list(disc.get("admin_role_ids", [])),
            admin_channel_id=int(get_secret("DISCORD_ADMIN_CHANNEL_ID") or disc.get("admin_channel_id", 0)),
            status_channel_id=int(get_secret("DISCORD_STATUS_CHANNEL_ID") or disc.get("status_channel_id", 0)),
            changefeed_channel_id=int(get_secret("DISCORD_CHANGEFEED_CHANNEL_ID") or disc.get("changefeed_channel_id", 0)),
            killfeed_channel_id=int(get_secret("DISCORD_KILLFEED_CHANNEL_ID") or disc.get("killfeed_channel_id", 0)),
            deathfeed_channel_id=int(get_secret("DISCORD_DEATHFEED_CHANNEL_ID") or disc.get("deathfeed_channel_id", 0)),
            server_status_channel_id=int(get_secret("DISCORD_SERVER_STATUS_CHANNEL_ID") or disc.get("server_status_channel_id", disc.get("status_channel_id", 0))),
            admin_log_channel_id=int(get_secret("DISCORD_ADMIN_LOG_CHANNEL_ID") or disc.get("admin_log_channel_id", 0)),
            loot_events_channel_id=int(get_secret("DISCORD_LOOT_EVENTS_CHANNEL_ID") or disc.get("loot_events_channel_id", 0)),
            use_presence=disc.get("use_presence", True),
            stat_channels_json=stat_channels_val,
        ),
        bot_mysql=MySQLSettings(
            host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", b_mysql.get("host", "mysql"))),
            port=int(os.getenv("MYSQL_PORT", b_mysql.get("port", 3306))),
            user=os.getenv("MYSQL_USER", b_mysql.get("user", "")),
            password=os.getenv("MYSQL_PASSWORD", b_mysql.get("password", "")),
            database=os.getenv("MYSQL_DATABASE", b_mysql.get("database", "")),
        ),
        nitrado_mysql=MySQLSettings(
            host=n_mysql.get("host", ""),
            port=int(n_mysql.get("port", 3306)),
            user=n_mysql.get("user", ""),
            password=n_mysql.get("password", ""),
            database=n_mysql.get("database", ""),
        ),
        org_id=service,
        server_name=conf_data.get("server_name", "DayZ Server"),
        platform=conf_data.get("platform", "pc"),
        killfeed_enabled=conf_data.get("killfeed_enabled", True),
        dayz_host=conf_data.get("query", {}).get("host", ""),
        dayz_query_port=int(conf_data.get("query", {}).get("port", 2302)),
        ftp_host=ftp_conf.get("host", ""),
        ftp_port=int(ftp_conf.get("port", 21)),
        ftp_user=ftp_user,
        ftp_password=ftp_password,
        ftp_log_path=ftp_conf.get("log_path", ""),
        ftp_base_path=ftp_conf.get("base_path", "/"),
        ftp_mission_path=ftp_conf.get("mission_path", ""),
        metrics_enabled=conf_data.get("metrics", {}).get("enabled", False),
        metrics_port=int(conf_data.get("metrics", {}).get("port", 9110)),
        a2s_timeout=float(conf_data.get("a2s", {}).get("timeout", 3.0)),
        a2s_retries=int(conf_data.get("a2s", {}).get("retries", 2)),
        a2s_retry_backoff=float(conf_data.get("a2s", {}).get("retry_backoff", 1.0)),
        a2s_cache_ttl=float(conf_data.get("a2s", {}).get("cache_ttl", 5.0)),
        a2s_port_offsets=conf_data.get("a2s", {}).get("port_offsets", [0]),
        vanilla_path=str(repo_root / "data" / "dayz_vanilla" / "official_repo" / "dayzOffline.chernarusplus"),
        mission_path=paths_conf.get("mission") or str(repo_root / "staging" / service / "dayzxb_missions" / "dayzOffline.chernarusplus"),
        ftp_ingest_local_path=paths_conf.get("ftp_ingest", "./staging/ezstreet"),
        state_dir=state_dir,
        chronos_root=repo_root,
        staging_dir=repo_root / "staging" / service,
        manifest_path=repo_root / "staging" / "deploy_manifest.json",
        vscode_settings_path=Path(os.path.expanduser("~/.config/Code - Insiders/User/settings.json")),
        vscode_extensions_dir=Path(os.path.expanduser("~/.vscode/extensions")),
    )


def get_settings() -> Settings:
    # Defaults to dev/ezstreet for now
    return load_settings()


# Aggressive reload test 1766859567
