from __future__ import annotations

import argparse
import os
import sys

from .a2s_client import query_info, query_players


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Probe A2S ports for a DayZ server (raw-first + fallback)"
    )
    ap.add_argument(
        "--host", default=os.getenv("DAYZ_HOST", ""), help="Server host/IP (defaults to DAYZ_HOST)"
    )
    ap.add_argument("--base-port", type=int, default=int(os.getenv("DAYZ_QUERY_PORT", "27016")))
    ap.add_argument("--offsets", default=os.getenv("A2S_PORT_OFFSETS", "0,1,2"))
    ap.add_argument("--timeout", type=float, default=float(os.getenv("A2S_TIMEOUT", "2.5")))
    ap.add_argument("--pad-to", type=int, default=int(os.getenv("A2S_PACKET_PAD_TO", "1200")))
    ap.add_argument(
        "--prefer-ipv4",
        action="store_true",
        default=os.getenv("A2S_PREFER_IPV4", "true").lower() in ("1", "true", "yes", "on"),
    )
    ap.add_argument(
        "--raw-enable",
        action="store_true",
        default=os.getenv("A2S_RAW_ENABLE", "true").lower() in ("1", "true", "yes", "on"),
    )
    args = ap.parse_args(argv)

    if not args.host:
        print("Missing --host (or DAYZ_HOST).", file=sys.stderr)
        return 2

    # Push CLI knobs into env so a2s_client/a2s_raw pick them up.
    os.environ["A2S_TIMEOUT"] = str(args.timeout)
    os.environ["A2S_PACKET_PAD_TO"] = str(args.pad_to)
    os.environ["A2S_PREFER_IPV4"] = "true" if args.prefer_ipv4 else "false"
    os.environ["A2S_RAW_ENABLE"] = "true" if args.raw_enable else "false"

    offsets = []
    for part in args.offsets.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            offsets.append(int(part))
        except ValueError:
            print(f"bad offset: {part!r}", file=sys.stderr)
            return 2

    ports = []
    for off in offsets:
        port = args.base_port + off
        if 1 <= port <= 65535 and port not in ports:
            ports.append(port)

    print(f"Host: {args.host}")
    print(f"Base: {args.base_port}")
    print(f"Offsets: {offsets}")
    print(f"Ports: {ports}")
    print(
        f"Timeout: {args.timeout}s  pad_to={args.pad_to}  prefer_ipv4={args.prefer_ipv4}  raw={args.raw_enable}"
    )
    print("")

    ok_any = False
    for port in ports:
        try:
            info = query_info(args.host, int(port))
            try:
                pcount = query_players(args.host, int(port))
            except Exception:
                # players often blocked even when info works; keep info result
                pcount = info.player_count

            ok_any = True
            print(
                f"OK  {port}  players={pcount}/{info.max_players}  map={info.map_name!r}  name={info.server_name!r}"
            )
        except Exception as e:
            print(f"NO  {port}  {type(e).__name__}: {e}")

    return 0 if ok_any else 1


if __name__ == "__main__":
    raise SystemExit(main())
