import asyncio
import websockets
import sys

async def test_ws():
    uri = "ws://localhost:18789/ws/logs"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.close()
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ws())
    sys.exit(0 if success else 1)
