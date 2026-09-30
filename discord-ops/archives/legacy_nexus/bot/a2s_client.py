from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .a2s_raw import query_info as raw_query_info
from .a2s_raw import query_players as raw_query_players

try:
    import a2s  # python-a2s
except Exception:  # pragma: no cover
    a2s = None


@dataclass
class A2SInfo:
    server_name: str
    map_name: str
    player_count: int
    max_players: int


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _iter_ports(base_port: int) -> list[int]:
    offs = os.getenv("A2S_PORT_OFFSETS", "0,1,2")
    out: list[int] = []
    for part in offs.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            off = int(part)
        except ValueError:
            continue
        p = base_port + off
        if 1 <= p <= 65535 and p not in out:
            out.append(p)
    return out or [base_port]


def _prefer_ipv4() -> bool:
    return _env_bool("A2S_PREFER_IPV4", True)


def _raw_enabled() -> bool:
    return _env_bool("A2S_RAW_ENABLE", True)


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _adapt_python_a2s_info(info: Any) -> A2SInfo:
    # python-a2s' object fields vary a bit by version; try common names.
    name = getattr(info, "server_name", None) or getattr(info, "name", None) or ""
    map_name = getattr(info, "map_name", None) or getattr(info, "map", None) or ""
    players = getattr(info, "player_count", None)
    if players is None:
        players = getattr(info, "players", None)
    maxp = getattr(info, "max_players", None)
    if maxp is None:
        maxp = getattr(info, "max", None)

    return A2SInfo(
        server_name=str(name),
        map_name=str(map_name),
        player_count=_as_int(players, 0),
        max_players=_as_int(maxp, 0),
    )


def query_info(host: str, port: int) -> A2SInfo:
    timeout_s = _env_float("A2S_TIMEOUT", 2.5)
    retries = _env_int("A2S_RETRIES", 2)
    pad_to = _env_int("A2S_PACKET_PAD_TO", 1200)
    prefer_ipv4 = _prefer_ipv4()

    ports = _iter_ports(int(port))
    last_err: Exception | None = None

    # 1) RAW first (recommended)
    if _raw_enabled():
        for p in ports:
            for _ in range(max(1, retries + 1)):
                try:
                    r = raw_query_info(
                        host, int(p), timeout_s=timeout_s, pad_to=pad_to, prefer_ipv4=prefer_ipv4
                    )
                    return A2SInfo(
                        server_name=r.server_name,
                        map_name=r.map_name,
                        player_count=int(r.player_count),
                        max_players=int(r.max_players),
                    )
                except Exception as e:
                    last_err = e

    # 2) Fallback python-a2s (if installed)
    if a2s is not None:
        for p in ports:
            for _ in range(max(1, retries + 1)):
                try:
                    info = a2s.info((host, int(p)), timeout=float(timeout_s))
                    return _adapt_python_a2s_info(info)
                except Exception as e:
                    last_err = e

    raise RuntimeError(f"A2S query_info failed for {host}:{port} ports={ports}: {last_err}")


def query_players(host: str, port: int) -> int:
    timeout_s = _env_float("A2S_TIMEOUT", 2.5)
    retries = _env_int("A2S_RETRIES", 2)
    pad_to = _env_int("A2S_PACKET_PAD_TO", 1200)
    prefer_ipv4 = _prefer_ipv4()

    ports = _iter_ports(int(port))
    last_err: Exception | None = None

    if _raw_enabled():
        for p in ports:
            for _ in range(max(1, retries + 1)):
                try:
                    return int(
                        raw_query_players(
                            host,
                            int(p),
                            timeout_s=timeout_s,
                            pad_to=pad_to,
                            prefer_ipv4=prefer_ipv4,
                        )
                    )
                except Exception as e:
                    last_err = e

    if a2s is not None:
        for p in ports:
            for _ in range(max(1, retries + 1)):
                try:
                    players = a2s.players((host, int(p)), timeout=float(timeout_s))
                    return len(players)
                except Exception as e:
                    last_err = e

    raise RuntimeError(f"A2S query_players failed for {host}:{port} ports={ports}: {last_err}")
