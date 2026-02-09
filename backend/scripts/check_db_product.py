import asyncio
from app.core.database import async_session
from app.models.data_product import DataProduct
from sqlalchemy import select


async def check():
    async with async_session() as db:
        res = await db.execute(select(DataProduct).where(DataProduct.id == 3))
        p = res.scalar()
        if p:
            print(f"ID: {p.id}")
            print(f"Name: {p.name}")
            print(f"Host: {p.grpc_host}")
            print(f"Port: {p.grpc_port}")
            print(f"Status: {p.connection_status}")
            print(f"Last Error: {p.last_error}")
        else:
            print("Product ID 3 not found")


if __name__ == "__main__":
    asyncio.run(check())
