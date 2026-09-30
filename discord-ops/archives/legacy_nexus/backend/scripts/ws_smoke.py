"""
WS Smoke Test (Contract Test)
Connects, waits for accept/hello, exits 0 on success, 1 on failure.
"""

import asyncio
import logging
import sys

import websockets

logging.basicConfig(level=logging.ERROR)


async def smoke_test():
    uri = "ws://localhost:19101/ws/logs"
    print(f"🚭 Smoking {uri}...")
    try:
        async with websockets.connect(uri, close_timeout=2) as websocket:
            print("✅ Connected")
            try:
                # Wait for at least one message or just hold for 2s to ensure stable connection
                # The server sends buffered logs immediately if any.
                # If buffer empty, we might time out waiting for msg.
                # But connection success is the primary smoke test here.
                # optionally wait for a "probe" response if we were hitting /ws/probe

                # Let's try to receive one message with short timeout
                msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"✅ Received data: {len(msg)} bytes")
            except TimeoutError:
                print("⚠️ Connected but no data received (Buffer empty?) - Connection OK")

            return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)
