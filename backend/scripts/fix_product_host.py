import asyncio
from app.core.database import async_session
from app.models.data_product import DataProduct
from sqlalchemy import select, update


async def fix():
    async with async_session() as db:
        await db.execute(
            update(DataProduct).where(DataProduct.id == 3).values(grpc_host="127.0.0.1")
        )
        await db.commit()
        print("Updated product 3 host to 127.0.0.1")


if __name__ == "__main__":
    asyncio.run(fix())
