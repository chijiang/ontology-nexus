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
        return await storage.search_instances(
            keyword=search_term, entity_type=class_name, limit=limit
        )


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
        return await storage.get_instances_by_class(entity_type=class_name, limit=limit)


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
        instance_name: Name or ID of the instance
        hops: Number of hops to traverse (default: 1)
        direction: Direction of traversal: 'incoming', 'outgoing', or 'both' (default: 'both')
        type: Optional, filter neighbors by entity type
        property_filter: Optional, filter neighbors by property values (e.g., {"status": "Open"})
    """
    async with get_storage() as storage:
        # Note: 'type' argument maps to 'entity_type' in storage
        kwargs = {
            "hops": hops,
            "direction": direction,
            "entity_type": type,
            "property_filter": property_filter,
        }
        if instance_name.isdigit():
            kwargs["entity_id"] = int(instance_name)
        else:
            kwargs["entity_name"] = instance_name

        return await storage.get_instance_neighbors(**kwargs)


@mcp.tool()
async def find_path_between_instances(
    start_name: str, end_name: str, max_depth: int = 5
) -> dict[str, Any] | None:
    """Find path between two instances.

    Args:
        start_name: Name or ID of start instance
        end_name: Name or ID of end instance
        max_depth: Maximum path length (default: 5)
    """
    async with get_storage() as storage:
        kwargs = {"max_depth": max_depth}
        if start_name.isdigit():
            kwargs["start_id"] = int(start_name)
        else:
            kwargs["start_name"] = start_name

        if end_name.isdigit():
            kwargs["end_id"] = int(end_name)
        else:
            kwargs["end_name"] = end_name

        return await storage.find_path_between_instances(**kwargs)


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


@mcp.tool()
async def structured_aggregation_query(
    target_class: str,
    aggregation: str = "count",
    aggregate_property: str | None = None,
    target_filters: dict[str, Any] | None = None,
    related_requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute complex aggregations (count, sum, avg, max, min) on graph entities.

    Supports filtering by the target entity's own properties AND by requiring connections
    to related entities with specific properties.

    Args:
        target_class: The primary entity class to aggregate over
        aggregation: Aggregation function: count, sum, avg, max, min
        aggregate_property: Property to aggregate on (required for sum, avg, max, min)
        target_filters: Filters on the target entity class itself
        related_requirements: List of related entity requirements, each with:
            related_class, relationship_type, direction (outgoing/incoming/both), filters

    Example:
        Count ServiceResponse where Product.product_group_ops=THINK:
        target_class="ServiceResponse", related_requirements=[{"related_class": "Product", "relationship_type": "PURCHASED", "direction": "outgoing", "filters": {"product_group_ops": "THINK"}}]
    """
    async with get_storage() as storage:
        return await storage.execute_complex_aggregation(
            target_class=target_class,
            aggregation=aggregation,
            aggregate_property=aggregate_property,
            target_filters=target_filters,
            related_requirements=related_requirements,
        )
