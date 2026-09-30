from __future__ import annotations

from dataclasses import dataclass

from rcon.battleye import Client as BERconClient  # type: ignore

@dataclass(frozen=True)
class RconResult:
    ok: bool
    response: str

def run_rcon(host: str, port: int, password: str, command: str, timeout_s: float = 3.0) -> RconResult:
    try:
        with BERconClient(host, port, passwd=password, timeout=timeout_s) as client:
            resp = client.run(command)
        return RconResult(ok=True, response=str(resp))
    except Exception as e:
        return RconResult(ok=False, response=f"{type(e).__name__}: {e}")
