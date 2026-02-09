import asyncio
import grpc.aio
import time


async def test_conn(target, timeout=5):
    print(f"Testing connection to {target}...")
    start = time.time()
    channel = grpc.aio.insecure_channel(target)
    try:
        await asyncio.wait_for(channel.channel_ready(), timeout=timeout)
        latency = (time.time() - start) * 1000
        print(f"SUCCESS: Connected to {target} in {latency:.2f}ms")
    except asyncio.TimeoutError:
        print(f"FAILED: Connection timeout to {target} after {timeout}s")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    finally:
        await channel.close()


async def main():
    await test_conn("localhost:6689")
    await test_conn("127.0.0.1:6689")
    await test_conn("[::1]:6689")


if __name__ == "__main__":
    asyncio.run(main())
