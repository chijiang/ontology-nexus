import asyncio
from app.core.database import async_session
from app.models.data_product import EntityMapping, PropertyMapping
from sqlalchemy import select


async def check():
    async with async_session() as db:
        res = await db.execute(
            select(EntityMapping).where(EntityMapping.data_product_id == 3)
        )
        entity_mappings = res.scalars().all()
        for em in entity_mappings:
            print(f"\nEntity Mapping: {em.ontology_class_name}")
            pm_res = await db.execute(
                select(PropertyMapping).where(
                    PropertyMapping.entity_mapping_id == em.id
                )
            )
            pms = pm_res.scalars().all()
            for pm in pms:
                print(f"  {pm.grpc_field} -> {pm.ontology_property}")


if __name__ == "__main__":
    asyncio.run(check())
