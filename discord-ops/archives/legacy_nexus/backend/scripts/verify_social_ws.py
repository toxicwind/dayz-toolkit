import asyncio
import json

import websockets


async def test_social_ws():
    uri = "ws://localhost:19101/ws/social"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            # The streamer should send the buffer history immediately
            try:
                while True:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(msg)
                    print(f"Received social event: {data.get('user')}: {data.get('message')}")
            except TimeoutError:
                print("No more buffered messages received (timeout).")
    except Exception as e:
        print(f"Failed to connect or receive: {e}")


if __name__ == "__main__":
    asyncio.run(test_social_ws())
