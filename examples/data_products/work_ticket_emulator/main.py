import asyncio
import logging
from work_ticket_emulator.grpc.server import serve

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
