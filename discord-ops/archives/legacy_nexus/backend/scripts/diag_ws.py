import asyncio

import websockets


async def test_ws(path):
    uri = f"ws://localhost:19101{path}"
    print(f"Testing {uri} WITHOUT Origin header...")
    try:
        async with websockets.connect(uri):
            print(f"✅ Success: {path}")
            return True
    except Exception as e:
        print(f"❌ Failed {path}: {e}")
        return False


async def main():
    await test_ws("/ws/logs")
    await test_ws("/ws/social")


if __name__ == "__main__":
    asyncio.run(main())
