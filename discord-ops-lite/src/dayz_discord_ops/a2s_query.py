from __future__ import annotations

import importlib.metadata
import logging
import socket
import time
from dataclasses import dataclass, replace
from typing import Any, Iterable, Tuple

log = logging.getLogger("dayz-discord-ops.a2s")

try:
    import a2s as _A2S_MODULE
except ModuleNotFoundError:  # pragma: no cover - exercised via tests with monkeypatch
    _A2S_MODULE = None

_A2S_CHECKED = False

@dataclass(frozen=True)
class A2SOptions:
    timeout_s: float = 2.0
    retries: int = 2
    retry_backoff: float = 1.5
    cache_ttl: int = 300

_OPTIONS = A2SOptions()

class A2SError(RuntimeError):
    """Base error for A2S wrapper failures."""

class A2SUnavailableError(A2SError):
    """Raised when the expected python-a2s dependency is missing or incompatible."""

class A2SQueryError(A2SError):
    """Raised when the remote server cannot be queried."""

    def __init__(self, message: str, *, reason: str = "unknown") -> None:
        super().__init__(message)
        self.reason = reason

@dataclass(frozen=True)
class A2SInfo:
    name: str
    map: str
    players: int
    max_players: int
    game: str
    version: str
    stale: bool = False
    last_error_reason: str | None = None

@dataclass(frozen=True)
class A2SPlayers:
    names: Tuple[str, ...]
    stale: bool = False
    last_error_reason: str | None = None

_CACHE_INFO: tuple[A2SInfo, float] | None = None
_CACHE_PLAYERS: tuple[A2SPlayers, float] | None = None

def configure(options: A2SOptions) -> None:
    global _OPTIONS
    _OPTIONS = options

def _detect_distribution_version() -> str:
    try:
        return importlib.metadata.version("python-a2s")
    except importlib.metadata.PackageNotFoundError:
        module = _A2S_MODULE
        if module is not None:
            return str(getattr(module, "__version__", "unknown"))
        return "unavailable"

def _ensure_module() -> Any:
    global _A2S_CHECKED
    module = _A2S_MODULE
    if module is None:
        raise A2SUnavailableError(
            "python-a2s is not installed. Install it with 'pip install python-a2s'."
        )

    missing = [attr for attr in ("info", "players") if not hasattr(module, attr)]
    if missing:
        raise A2SUnavailableError(
            "Installed 'a2s' package is incompatible (missing: "
            + ", ".join(missing)
            + "). Ensure python-a2s>=1.3.0 is installed and remove the legacy 'a2s' package."
        )

    if not _A2S_CHECKED:
        _A2S_CHECKED = True
        log.info("Using python-a2s %s", _detect_distribution_version())

    return module

def _wrap_call(func_name: str, addr: tuple[str, int], timeout_s: float) -> Any:
    module = _ensure_module()
    func = getattr(module, func_name)
    try:
        return func(addr, timeout=timeout_s)
    except socket.timeout as exc:
        raise A2SQueryError(
            f"A2S {func_name} timed out for {addr[0]}:{addr[1]} (timeout={timeout_s})",
            reason="timeout",
        ) from exc
    except ConnectionError as exc:
        raise A2SQueryError(
            f"A2S {func_name} connection failed for {addr[0]}:{addr[1]}: {exc}",
            reason="connection",
        ) from exc
    except OSError as exc:
        raise A2SQueryError(
            f"A2S {func_name} socket error for {addr[0]}:{addr[1]}: {exc}",
            reason="oserror",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        raise A2SQueryError(
            f"A2S {func_name} raised unexpected {type(exc).__name__}: {exc}",
            reason="unexpected",
        ) from exc

def _query_with_retry(func_name: str, addr: tuple[str, int]) -> Any:
    timeout = _OPTIONS.timeout_s
    last_error: A2SQueryError | None = None
    attempts = max(1, _OPTIONS.retries + 1)
    for _ in range(attempts):
        try:
            return _wrap_call(func_name, addr, timeout)
        except A2SQueryError as exc:
            last_error = exc
            timeout *= max(1.0, _OPTIONS.retry_backoff)
    assert last_error is not None  # noqa: S101
    raise last_error

def _cache_valid(cache: tuple[Any, float] | None, now: float) -> tuple[Any, bool]:
    if not cache:
        return None, False
    item, ts = cache
    if now - ts <= max(0, _OPTIONS.cache_ttl):
        return item, True
    return None, False

def query_info(host: str, port: int) -> A2SInfo:
    global _CACHE_INFO
    addr = (host, port)
    now = time.time()
    try:
        info_raw: Any = _query_with_retry("info", addr)
    except A2SQueryError as exc:
        cached, ok = _cache_valid(_CACHE_INFO, now)
        if ok and cached:
            log.warning("A2S info fallback to cached data: %s", exc)
            return replace(
                cached,
                stale=True,
                last_error_reason=exc.reason,
            )
        raise

    result = A2SInfo(
        name=str(info_raw.server_name),
        map=str(info_raw.map_name),
        players=int(info_raw.player_count),
        max_players=int(info_raw.max_players),
        game=str(info_raw.game),
        version=str(getattr(info_raw, "version", "")),
        stale=False,
        last_error_reason=None,
    )

    _CACHE_INFO = (result, now)
    return result

def query_players(host: str, port: int) -> A2SPlayers:
    global _CACHE_PLAYERS
    addr = (host, port)
    now = time.time()
    try:
        players_raw: Iterable[Any] = _query_with_retry("players", addr)
    except A2SQueryError as exc:
        cached, ok = _cache_valid(_CACHE_PLAYERS, now)
        if ok and cached:
            log.warning("A2S players fallback to cached data: %s", exc)
            return replace(cached, stale=True, last_error_reason=exc.reason)
        raise

    names: list[str] = []
    for p in players_raw:
        nm = getattr(p, "name", "") or ""
        nm = nm.strip()
        if nm:
            names.append(nm)

    result = A2SPlayers(names=tuple(names))
    _CACHE_PLAYERS = (result, now)
    return result
