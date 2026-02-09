import asyncio
from sqlalchemy import text
from app.core.database import async_session


async def check():
    async with async_session() as db:
        res = await db.execute(
            text(
                "SELECT id, source_id, target_id, relationship_type FROM graph_relationships LIMIT 10"
            )
        )
        for row in res:
            print(row)

        res = await db.execute(
            text(
                "SELECT id, name, entity_type FROM graph_entities WHERE id IN (SELECT source_id FROM graph_relationships LIMIT 10) OR id IN (SELECT target_id FROM graph_relationships LIMIT 10)"
            )
        )
        for row in res:
            print(f"Entity: {row}")


if __name__ == "__main__":
    asyncio.run(check())
