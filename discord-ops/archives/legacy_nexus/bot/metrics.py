from __future__ import annotations

from prometheus_client import Counter, Gauge, start_http_server

A2S_UP = Gauge("dayz_a2s_up", "Whether A2S query succeeded (1/0)")
A2S_STALE = Gauge("dayz_a2s_stale", "Whether cached (stale) A2S data is being used (1/0)")
A2S_PLAYERS = Gauge("dayz_a2s_players", "Players reported via A2S")
A2S_MAX_PLAYERS = Gauge("dayz_a2s_max_players", "Max players reported via A2S")
A2S_ERRORS = Counter("dayz_a2s_errors_total", "A2S query failures by reason", ["reason"])

# Performance & Diagnostics
SERVER_FPS = Gauge("dayz_server_fps", "Current server FPS (from RPT)")
MEMORY_VIRT = Gauge("dayz_memory_virt_mb", "Virtual memory usage in MB")
MEMORY_PHYS = Gauge("dayz_memory_phys_mb", "Physical memory usage in MB")
SEARCH_OVERTIME = Counter("dayz_search_overtime_total", "Items causing search overtime", ["item"])
HARD_TO_PLACE = Counter("dayz_hard_to_place_total", "Items hard to place", ["item"])
SCRIPT_ERRORS = Counter("dayz_script_errors_total", "Script errors and warnings", ["level"])

def start_metrics(port: int) -> None:
    start_http_server(port)
