from contextlib import asynccontextmanager
from typing import AsyncIterator, Any
import logging

from fastmcp import FastMCP
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.services.graph_tools import GraphTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Query Server")

# Resource management
@asynccontextmanager
async def make_neo4j_session() -> AsyncIterator[Any]:
    """Create a Neo4j session context manager."""
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    try:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            yield session
    finally:
        await driver.close()

async def get_graph_tools() -> GraphTools:
    """Helper to get initialized GraphTools instance."""
    # We need to manually handle the session lifecycle for each tool call
    # Since GraphTools expects a session, we'll create a driver and session per request
    # This is a bit overhead but ensures clean connection management
    # For a production server, we might want to use a shared driver
    pass

# Initialize shared driver
driver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
)

@asynccontextmanager
async def get_session():
    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        yield session

@mcp.tool()
async def search_instances(search_term: str, class_name: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Search for instances in the Knowledge Graph.

    Args:
        search_term: Keyword to search for (e.g., Order ID, Supplier Name)
        class_name: Optional, limit search to specific entity type
        limit: Number of results to return (default: 10)
    """
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.search_instances(search_term, class_name, limit)

@mcp.tool()
async def get_instances_by_class(class_name: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get all instances of a specific class.

    Args:
        class_name: Class name (e.g., PurchaseOrder, Supplier)
        limit: Number of results to return (default: 20)
    """
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.get_instances_by_class(class_name, limit=limit)

@mcp.tool()
async def get_instance_neighbors(instance_name: str, hops: int = 1, direction: str = "both") -> dict[str, Any]:
    """Get neighbors of an instance.

    Args:
        instance_name: Name of the instance
        hops: Number of hops to traverse (default: 1)
        direction: Direction of traversal: 'incoming', 'outgoing', or 'both' (default: 'both')
    """
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.get_instance_neighbors(instance_name, hops, direction)

@mcp.tool()
async def find_path_between_instances(start_name: str, end_name: str, max_depth: int = 5) -> dict[str, Any]:
    """Find path between two instances.

    Args:
        start_name: Name of start instance
        end_name: Name of end instance
        max_depth: Maximum path length (default: 5)
    """
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.find_path_between_instances(start_name, end_name, max_depth)

@mcp.tool()
async def describe_class(class_name: str) -> dict[str, Any]:
    """Get definition of a class.

    Args:
        class_name: Name of the class to describe
    """
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.describe_class(class_name)

@mcp.tool()
async def get_ontology_classes() -> list[dict[str, Any]]:
    """Get all classes defined in the ontology."""
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.get_ontology_classes()

@mcp.tool()
async def get_ontology_relationships() -> list[dict[str, Any]]:
    """Get all relationships defined in the ontology."""
    async with get_session() as session:
        tools = GraphTools(session=session)
        return await tools.get_ontology_relationships()
