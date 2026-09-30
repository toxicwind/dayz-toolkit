import asyncio

import websockets


async def test_ws():
    uri = "ws://localhost:19101/ws/logs"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            # Convert headers/params if needed? No, handshake should be open.

            # Wait for a message
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received message: {msg[:100]}...")
            except TimeoutError:
                print("Timeout waiting for log message (Server might be quiet)")

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_ws())
