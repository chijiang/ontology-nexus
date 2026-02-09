import asyncio
from app.core.database import async_session
from app.models.graph import GraphEntity
from sqlalchemy import select


async def check():
    async with async_session() as db:
        res = await db.execute(
            select(GraphEntity).where(GraphEntity.name == "OfficePro Supplies")
        )
        entity = res.scalar_one_or_none()
        if entity:
            print(f"ID: {entity.id}")
            print(f"Type: {entity.entity_type}")
            print(f"Properties: {entity.properties}")
        else:
            print("Entity 'OfficePro Supplies' not found")


if __name__ == "__main__":
    asyncio.run(check())
