from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RconResult:
    ok: bool
    response: str


def run_rcon(host: str, port: int, password: str, command: str, timeout_s: float = 3.0) -> RconResult:
    """
    RCON is disabled for the console-focused build. This stub exists so optional
    PC/local users can replace it with a real implementation under extras.
    """
    return RconResult(ok=False, response="RCON disabled in console build")
