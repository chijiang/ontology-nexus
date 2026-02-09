import asyncio
from sqlalchemy import text
from app.core.database import async_session


async def check():
    async with async_session() as db:
        res = await db.execute(
            text(
                "SELECT id, name, properties FROM graph_entities WHERE name = 'PO-0017'"
            )
        )
        row = res.first()
        print(f"PO-0017: {row}")
        if row and row[2]:
            print(f"Properties id: {row[2].get('id')}")


if __name__ == "__main__":
    asyncio.run(check())
