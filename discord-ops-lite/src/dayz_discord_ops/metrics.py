from __future__ import annotations

from prometheus_client import Counter, Gauge, start_http_server

A2S_UP = Gauge("dayz_a2s_up", "Whether A2S query succeeded (1/0)")
A2S_STALE = Gauge("dayz_a2s_stale", "Whether cached (stale) A2S data is being used (1/0)")
A2S_PLAYERS = Gauge("dayz_a2s_players", "Players reported via A2S")
A2S_MAX_PLAYERS = Gauge("dayz_a2s_max_players", "Max players reported via A2S")
A2S_ERRORS = Counter("dayz_a2s_errors_total", "A2S query failures by reason", ["reason"])
RCON_UP = Gauge("dayz_rcon_up", "Whether RCON command succeeded (1/0)")
RCON_ERRORS = Counter("dayz_rcon_errors_total", "RCON failures")

def start_metrics(port: int) -> None:
    start_http_server(port)
