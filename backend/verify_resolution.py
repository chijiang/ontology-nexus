import asyncio
from sqlalchemy import text
from app.api.actions import ActionExecutionRequest
from app.services.pg_graph_storage import PGGraphStorage
from app.core.database import async_session


async def verify_resolution():
    async with async_session() as db:
        storage = PGGraphStorage(db)

        # Test case 1: Resolve PO-0017
        name = "PO-0017"
        entity_type = "PurchaseOrder"

        resolved = await storage.get_entity_by_name(name, entity_type)
        if resolved:
            print(f"SUCCESS: Resolved {name} to ID {resolved['id']}")
            print(f"Type of ID: {type(resolved['id'])}")
        else:
            print(f"FAILURE: Could not resolve {name}")


if __name__ == "__main__":
    asyncio.run(verify_resolution())
