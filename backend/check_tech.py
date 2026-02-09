import asyncio
from sqlalchemy import text
from app.core.database import async_session


async def check():
    async with async_session() as db:
        res = await db.execute(
            text("SELECT properties FROM graph_entities WHERE name = 'TechSupply Corp'")
        )
        print(f"TechSupply Corp: {res.scalar()}")


if __name__ == "__main__":
    asyncio.run(check())
