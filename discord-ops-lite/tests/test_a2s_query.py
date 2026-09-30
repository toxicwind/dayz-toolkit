from __future__ import annotations

import socket
from types import SimpleNamespace

import pytest

from dayz_discord_ops import a2s_query


def _patch_module(monkeypatch: pytest.MonkeyPatch, module: object | None) -> None:
    monkeypatch.setattr(a2s_query, "_A2S_MODULE", module, raising=False)
    monkeypatch.setattr(a2s_query, "_A2S_CHECKED", False, raising=False)
    monkeypatch.setattr(a2s_query, "_CACHE_INFO", None, raising=False)
    monkeypatch.setattr(a2s_query, "_CACHE_PLAYERS", None, raising=False)
    a2s_query.configure(a2s_query.A2SOptions(cache_ttl=60, timeout_s=0.1, retries=0, retry_backoff=1.0))


def test_query_info_missing_module(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_module(monkeypatch, None)
    with pytest.raises(a2s_query.A2SUnavailableError):
        a2s_query.query_info("127.0.0.1", 27015)


def test_query_info_detects_legacy_package(monkeypatch: pytest.MonkeyPatch) -> None:
    legacy_module = SimpleNamespace(info=lambda *args, **kwargs: None)
    _patch_module(monkeypatch, legacy_module)
    with pytest.raises(a2s_query.A2SUnavailableError):
        a2s_query.query_players("127.0.0.1", 27015)


def test_query_info_wraps_socket_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout_info(*args: object, **kwargs: object) -> None:
        raise socket.timeout("boom")

    fake_module = SimpleNamespace(info=_timeout_info, players=lambda *a, **k: [])
    _patch_module(monkeypatch, fake_module)

    with pytest.raises(a2s_query.A2SQueryError) as excinfo:
        a2s_query.query_info("127.0.0.1", 27015)
    assert excinfo.value.reason == "timeout"


def test_query_players_strips_names(monkeypatch: pytest.MonkeyPatch) -> None:
    info_obj = SimpleNamespace(
        server_name="S",
        map_name="m",
        player_count=2,
        max_players=10,
        game="DayZ",
        version="1.0",
    )

    def _info(*args: object, **kwargs: object) -> SimpleNamespace:
        return info_obj

    def _players(*args: object, **kwargs: object) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(name=" Alice "),
            SimpleNamespace(name=""),
            SimpleNamespace(name=None),
            SimpleNamespace(name="Bob"),
        ]

    fake_module = SimpleNamespace(info=_info, players=_players)
    _patch_module(monkeypatch, fake_module)

    result = a2s_query.query_info("127.0.0.1", 27015)
    assert result.players == 2
    assert result.max_players == 10
    assert not result.stale

    players = a2s_query.query_players("127.0.0.1", 27015)
    assert list(players.names) == ["Alice", "Bob"]
    assert not players.stale


def test_query_info_cache_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    info_obj = SimpleNamespace(
        server_name="Live",
        map_name="cherno",
        player_count=10,
        max_players=60,
        game="DayZ",
        version="1.29",
    )

    def _info_ok(*args: object, **kwargs: object) -> SimpleNamespace:
        return info_obj

    fake_module = SimpleNamespace(info=_info_ok, players=lambda *a, **k: [])
    _patch_module(monkeypatch, fake_module)

    first = a2s_query.query_info("127.0.0.1", 27015)
    assert not first.stale

    def _info_fail(*args: object, **kwargs: object) -> None:
        raise socket.timeout("boom")

    fake_module_fail = SimpleNamespace(info=_info_fail, players=lambda *a, **k: [])
    monkeypatch.setattr(a2s_query, "_A2S_MODULE", fake_module_fail, raising=False)
    monkeypatch.setattr(a2s_query, "_A2S_CHECKED", True, raising=False)

    cached = a2s_query.query_info("127.0.0.1", 27015)
    assert cached.stale
    assert cached.last_error_reason == "timeout"


def test_query_players_cache_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _players_ok(*args: object, **kwargs: object) -> list[SimpleNamespace]:
        return [SimpleNamespace(name="One")]

    fake_module = SimpleNamespace(info=lambda *a, **k: SimpleNamespace(), players=_players_ok)
    _patch_module(monkeypatch, fake_module)
    fresh = a2s_query.query_players("127.0.0.1", 27015)
    assert not fresh.stale

    def _players_fail(*args: object, **kwargs: object) -> None:
        raise socket.timeout("players boom")

    monkeypatch.setattr(a2s_query, "_A2S_MODULE", SimpleNamespace(info=lambda *a, **k: None, players=_players_fail), raising=False)
    monkeypatch.setattr(a2s_query, "_A2S_CHECKED", True, raising=False)

    cached = a2s_query.query_players("127.0.0.1", 27015)
    assert cached.stale
    assert cached.last_error_reason == "timeout"
    assert list(cached.names) == ["One"]
