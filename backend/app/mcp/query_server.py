from contextlib import asynccontextmanager
import logging
from typing import Any

from fastmcp import FastMCP

from app.core.database import async_session
from app.services.pg_graph_storage import PGGraphStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Query Server")


@asynccontextmanager
async def get_storage():
    """Context manager for PGGraphStorage with its own session."""
    async with async_session() as session:
        yield PGGraphStorage(session)


@mcp.tool()
async def search_instances(
    search_term: str, class_name: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Search for instances in the Knowledge Graph.

    Args:
        search_term: Keyword to search for (e.g., Order ID, Supplier Name)
        class_name: Optional, limit search to specific entity type
        limit: Number of results to return (default: 10)
    """
    async with get_storage() as storage:
        return await storage.search_instances(search_term, class_name, limit)


@mcp.tool()
async def get_instances_by_class(
    class_name: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Get all instances of a specific class.

    Args:
        class_name: Class name (e.g., PurchaseOrder, Supplier)
        limit: Number of results to return (default: 20)
    """
    async with get_storage() as storage:
        return await storage.get_instances_by_class(class_name, limit=limit)


@mcp.tool()
async def get_instance_neighbors(
    instance_name: str,
    hops: int = 1,
    direction: str = "both",
    type: str | None = None,
    property_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Get neighbors of an instance.

    Args:
        instance_name: Name of the instance
        hops: Number of hops to traverse (default: 1)
        direction: Direction of traversal: 'incoming', 'outgoing', or 'both' (default: 'both')
        type: Optional, filter neighbors by entity type
        property_filter: Optional, filter neighbors by property values (e.g., {"status": "Open"})
    """
    async with get_storage() as storage:
        # Note: 'type' argument maps to 'entity_type' in storage
        return await storage.get_instance_neighbors(
            instance_name,
            hops,
            direction,
            entity_type=type,
            property_filter=property_filter,
        )


@mcp.tool()
async def find_path_between_instances(
    start_name: str, end_name: str, max_depth: int = 5
) -> dict[str, Any] | None:
    """Find path between two instances.

    Args:
        start_name: Name of start instance
        end_name: Name of end instance
        max_depth: Maximum path length (default: 5)
    """
    async with get_storage() as storage:
        return await storage.find_path_between_instances(
            start_name, end_name, max_depth
        )


@mcp.tool()
async def describe_class(class_name: str) -> dict[str, Any]:
    """Get definition of a class.

    Args:
        class_name: Name of the class to describe
    """
    async with get_storage() as storage:
        return await storage.describe_class(class_name)


@mcp.tool()
async def get_ontology_classes() -> list[dict[str, Any]]:
    """Get all classes defined in the ontology."""
    async with get_storage() as storage:
        return await storage.get_ontology_classes()


@mcp.tool()
async def get_ontology_relationships() -> list[dict[str, Any]]:
    """Get all relationships defined in the ontology."""
    async with get_storage() as storage:
        return await storage.get_ontology_relationships()
