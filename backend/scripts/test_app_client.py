import asyncio
from app.services.grpc_client import DynamicGrpcClient


async def test():
    print("Testing with DynamicGrpcClient on localhost:6689...")
    client = DynamicGrpcClient("localhost", 6689)
    try:
        await client.connect(timeout=2)
        print("SUCCESS: Connected to localhost:6689")
        await client.close()
    except Exception as e:
        print(f"FAILED: {e}")

    print("\nTesting with DynamicGrpcClient on 127.0.0.1:6689...")
    client = DynamicGrpcClient("127.0.0.1", 6689)
    try:
        await client.connect(timeout=2)
        print("SUCCESS: Connected to 127.0.0.1:6689")
        await client.close()
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test())
