"""
WS Smoke Client (Proof of Sink 2)
Connects to backend WS, waits for messages, prints them.
"""

import asyncio
import json
import logging
import sys

import websockets

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ws_client")


async def listen(duration=10):
    uri = "ws://localhost:19101/ws/logs"
    log.info(f"Connecting to {uri}...")
    end_time = asyncio.get_event_loop().time() + duration

    while asyncio.get_event_loop().time() < end_time:
        try:
            async with websockets.connect(uri) as websocket:
                log.info("Connected to Event Fabric Sink (WS)")

                while asyncio.get_event_loop().time() < end_time:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(msg)
                        print(f"WS_RECV: {json.dumps(data)}")
                    except TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        log.error("Connection closed, retrying...")
                        break
                return  # Success/Done
        except (OSError, websockets.exceptions.InvalidHandshake, websockets.exceptions.InvalidStatusCode) as e:
            log.warning(f"Connection failed ({e}), retrying in 2s...")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(listen(int(sys.argv[1]) if len(sys.argv) > 1 else 10))
