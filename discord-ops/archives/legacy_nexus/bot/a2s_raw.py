from __future__ import annotations

import ipaddress
import logging
import socket
import struct
import time
from dataclasses import dataclass
from typing import Iterable

log = logging.getLogger("dayz-discord-ops.a2s-raw")


class A2SRawError(RuntimeError):
    """Base error for raw A2S implementation."""


class A2SRawTimeout(A2SRawError):
    """Raised when the server does not respond in time."""


class A2SRawProtocolError(A2SRawError):
    """Raised when the server responds with an unexpected packet."""


_HDR_SINGLE = b"\xff\xff\xff\xff"
_HDR_SPLIT = b"\xfe\xff\xff\xff"  # -2 (little-endian)


@dataclass(frozen=True)
class RawInfo:
    server_name: str
    map_name: str
    player_count: int
    max_players: int
    game: str
    version: str
    # useful for diagnostics
    resolved_ip: str
    query_port: int


@dataclass(frozen=True)
class RawPlayer:
    name: str


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _resolve_ipv4(host: str) -> list[str]:
    if _is_ip(host):
        return [host]
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_DGRAM):
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
    except socket.gaierror:
        return []
    return ips


def _pad_packet(payload: bytes, pad_to: int) -> bytes:
    if pad_to <= 0:
        return payload
    # Keep within typical MTU-friendly sizes.
    pad_to = min(max(pad_to, len(payload)), 1400)
    if len(payload) >= pad_to:
        return payload
    return payload + (b"\x00" * (pad_to - len(payload)))


def _read_cstring(buf: bytes, idx: int) -> tuple[str, int]:
    end = buf.find(b"\x00", idx)
    if end == -1:
        raise A2SRawProtocolError("missing cstring terminator")
    try:
        return buf[idx:end].decode("utf-8", errors="replace"), end + 1
    except Exception as exc:
        raise A2SRawProtocolError(f"failed to decode cstring: {exc}") from exc


def _recv_exact(sock: socket.socket, timeout_s: float) -> bytes:
    sock.settimeout(timeout_s)
    try:
        data, _ = sock.recvfrom(65535)
        return data
    except socket.timeout as exc:
        raise A2SRawTimeout("socket timeout") from exc


def _recv_response(sock: socket.socket, timeout_s: float) -> bytes:
    """Receive a full A2S response, assembling split packets when needed."""
    first = _recv_exact(sock, timeout_s)
    if first.startswith(_HDR_SINGLE):
        return first

    if not first.startswith(_HDR_SPLIT):
        raise A2SRawProtocolError("unexpected packet header")

    # Source split format:
    # - header (-2)
    # - request_id (int32)
    # - total (uint8)
    # - number (uint8)
    # - size (uint16) [present for Source]
    # - payload...
    if len(first) < 12:
        raise A2SRawProtocolError("split packet too short")

    req_id = struct.unpack_from("<i", first, 4)[0]
    total = first[8]
    number = first[9]
    # size = struct.unpack_from("<H", first, 10)[0]
    payload = first[12:]

    parts: dict[int, bytes] = {number: payload}
    deadline = time.monotonic() + timeout_s
    while len(parts) < total:
        remaining = max(0.05, deadline - time.monotonic())
        pkt = _recv_exact(sock, remaining)
        if not pkt.startswith(_HDR_SPLIT) or len(pkt) < 12:
            continue
        pkt_req_id = struct.unpack_from("<i", pkt, 4)[0]
        if pkt_req_id != req_id:
            continue
        pkt_number = pkt[9]
        parts[pkt_number] = pkt[12:]

    return _HDR_SINGLE + b"".join(parts[i] for i in sorted(parts))


def _send_and_recv(host: str, port: int, payload: bytes, *, timeout_s: float, prefer_ipv4: bool) -> tuple[bytes, str]:
    targets = [host]
    if prefer_ipv4:
        ips = _resolve_ipv4(host)
        if ips:
            targets = ips

    last_err: Exception | None = None
    for ip in targets:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(payload, (ip, port))
            resp = _recv_response(sock, timeout_s)
            return resp, ip
        except Exception as exc:
            last_err = exc
        finally:
            sock.close()

    if last_err is None:
        raise A2SRawTimeout("no targets")
    raise last_err


def query_info(host: str, port: int, *, timeout_s: float, pad_to: int, prefer_ipv4: bool) -> RawInfo:
    # A2S_INFO request
    req = _HDR_SINGLE + b"TSource Engine Query\x00"
    req = _pad_packet(req, pad_to)

    resp, ip = _send_and_recv(host, port, req, timeout_s=timeout_s, prefer_ipv4=prefer_ipv4)
    if not resp.startswith(_HDR_SINGLE):
        raise A2SRawProtocolError("invalid header")

    # 0x41 = S2C_CHALLENGE
    if len(resp) >= 9 and resp[4] == 0x41:
        challenge = resp[5:9]
        req2 = _HDR_SINGLE + b"TSource Engine Query\x00" + challenge
        req2 = _pad_packet(req2, pad_to)
        resp, ip = _send_and_recv(host, port, req2, timeout_s=timeout_s, prefer_ipv4=prefer_ipv4)

    if len(resp) < 6:
        raise A2SRawProtocolError("short A2S_INFO response")
    if resp[4] not in (0x49, 0x6D):
        raise A2SRawProtocolError(f"unexpected A2S_INFO response type: 0x{resp[4]:02x}")

    idx = 5
    # protocol byte
    idx += 1
    server_name, idx = _read_cstring(resp, idx)
    map_name, idx = _read_cstring(resp, idx)
    _folder, idx = _read_cstring(resp, idx)
    game, idx = _read_cstring(resp, idx)
    # game id
    if idx + 2 > len(resp):
        raise A2SRawProtocolError("truncated game id")
    idx += 2
    if idx + 3 > len(resp):
        raise A2SRawProtocolError("truncated player fields")
    player_count = resp[idx]
    max_players = resp[idx + 1]
    # bots = resp[idx+2]
    idx += 3
    # server type / environment / visibility / vac
    if idx + 4 > len(resp):
        raise A2SRawProtocolError("truncated server flags")
    idx += 4
    version = ""
    try:
        version, idx = _read_cstring(resp, idx)
    except Exception:
        version = ""

    return RawInfo(
        server_name=server_name,
        map_name=map_name,
        player_count=int(player_count),
        max_players=int(max_players),
        game=game,
        version=version,
        resolved_ip=ip,
        query_port=port,
    )


def query_players(host: str, port: int, *, timeout_s: float, pad_to: int, prefer_ipv4: bool) -> list[RawPlayer]:
    # A2S_PLAYER request uses 0x55 ('U')
    # First request with challenge = -1, then retry with returned challenge.
    req = _HDR_SINGLE + b"U" + struct.pack("<i", -1)
    req = _pad_packet(req, pad_to)
    resp, _ip = _send_and_recv(host, port, req, timeout_s=timeout_s, prefer_ipv4=prefer_ipv4)

    if len(resp) < 9 or resp[4] != 0x41:
        raise A2SRawProtocolError("expected S2C_CHALLENGE for A2S_PLAYER")
    challenge = resp[5:9]
    req2 = _HDR_SINGLE + b"U" + challenge
    req2 = _pad_packet(req2, pad_to)
    resp, _ip = _send_and_recv(host, port, req2, timeout_s=timeout_s, prefer_ipv4=prefer_ipv4)
    if len(resp) < 6 or resp[4] != 0x44:
        raise A2SRawProtocolError("unexpected A2S_PLAYER response")

    idx = 5
    num = resp[idx]
    idx += 1
    out: list[RawPlayer] = []
    for _ in range(int(num)):
        if idx >= len(resp):
            break
        idx += 1  # index
        name, idx = _read_cstring(resp, idx)
        # score (int32) + duration (float)
        if idx + 8 > len(resp):
            break
        idx += 8
        nm = name.strip()
        if nm:
            out.append(RawPlayer(name=nm))
    return out
