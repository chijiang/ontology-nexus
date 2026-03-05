"""Query tools for the enhanced agent.

These tools wrap the PostgreSQL graph storage functionality into LangChain-compatible tools.
Neo4j has been removed in favor of PostgreSQL + SQL/PGQ.
"""

from typing import Any, Callable, Optional, Dict, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.pg_graph_storage import PGGraphStorage


class SearchInstancesInput(BaseModel):
    """Input for search_instances tool."""

    search_term: str = Field(
        description="Search keyword, e.g., order ID, supplier name, etc."
    )
    class_name: str | None = Field(
        None, description="Optional, restrict search to a specific entity type"
    )
    limit: int = Field(10, description="Number of results to return, default 10")


class GetInstancesByClassInput(BaseModel):
    """Input for get_instances_by_class tool."""

    class_name: str = Field(
        description="Class name, e.g., PurchaseOrder, Supplier, etc."
    )
    limit: int = Field(20, description="Number of results to return, default 20")


class GetInstanceNeighborsInput(BaseModel):
    """Input for get_instance_neighbors tool."""

    instance_name: str = Field(description="Instance name, e.g., PO_2024_001")
    hops: int = Field(1, description="Number of hops, default 1")
    direction: str = Field(
        "both",
        description="Direction: both, outgoing or incoming. Use 'both' if uncertain, or check ontology definitions first.",
    )
    type: str | None = Field(None, description="Optional, specify neighbor entity type")
    property_filter: Dict[str, Any] | None = Field(
        None, description="Optional, filter target properties, e.g., {'status': 'Open'}"
    )


class FindPathInput(BaseModel):
    """Input for find_path_between_instances tool."""

    start_name: str = Field(description="Start instance name")
    end_name: str = Field(description="Goal instance name")
    max_depth: int = Field(5, description="Maximum depth, default 5")


class DescribeClassInput(BaseModel):
    """Input for describe_class tool."""

    class_name: str = Field(description="Class name, e.g., PurchaseOrder")


class GetNodeStatisticsInput(BaseModel):
    """Input for get_node_statistics tool."""

    node_label: str | None = Field(
        None, description="Optional, specify node type for statistics"
    )


class EmptyInput(BaseModel):
    """Empty input for tools that don't need parameters."""

    pass


async def _execute_with_session(
    get_session_func: Callable,
    func: Callable[[PGGraphStorage], Any],
    event_emitter: Any = None,
) -> Any:
    """Execute a function with a PostgreSQL graph storage instance."""
    session_cm = get_session_func()
    async with session_cm as session:
        storage = PGGraphStorage(session, event_emitter)
        return await func(storage)


def create_query_tools(
    get_session_func: Callable[[], Any], event_emitter: Any = None
) -> list[StructuredTool]:
    """Create LangChain-compatible query tools."""

    async def search_instances(
        search_term: str, class_name: str | None = None, limit: int = 10
    ) -> str:
        """Search for entity instances in the knowledge graph."""

        async def _execute(tools) -> str:
            results = await tools.search_instances(
                keyword=search_term, entity_type=class_name, limit=limit
            )
            if not results:
                return f"No matches found for '{search_term}'"
            output = [f"Found {len(results)} matches for '{search_term}':\n"]
            for r in results[:10]:
                name = r.get("name", "N/A")
                db_id = r.get("id", "N/A")
                labels = (
                    r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                )
                props = r.get("properties", {})
                props_str = ", ".join(
                    [f"{k}={v}" for k, v in props.items() if not k.startswith("__")]
                )
                output.append(
                    f"  - ID: {db_id}, Name: {name} (Type: {labels}, {props_str})"
                )
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_instances_by_class(class_name: str, limit: int = 20) -> str:
        """Get all instances of a specified type."""

        async def _execute(tools) -> str:
            results = await tools.get_instances_by_class(
                entity_type=class_name, property_filter=None, limit=limit
            )
            if not results:
                return f"No instances found for type '{class_name}'."
            output = [f"Found {len(results)} instances of type '{class_name}':\n"]
            for r in results[:15]:
                name = r.get("name", "N/A")
                db_id = r.get("id", "N/A")
                props = r.get("properties", {})
                props_str = ", ".join(
                    [f"{k}={v}" for k, v in props.items() if not k.startswith("__")]
                )
                output.append(f"  - ID: {db_id}, Name: {name} ({props_str})")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_instance_neighbors(
        instance_name: str,
        hops: int = 1,
        direction: str = "both",
        type: str | None = None,
        property_filter: Dict[str, Any] | None = None,
    ) -> str:
        """Query neighbor nodes of an instance."""

        async def _execute(tools) -> str:
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

            results = await tools.get_instance_neighbors(**kwargs)
            if not results:
                return f"No neighbor nodes found for '{instance_name}'"

            # Group by distance
            by_distance = {}
            for r in results:
                dist = r.get("distance", 1)
                if dist not in by_distance:
                    by_distance[dist] = []
                by_distance[dist].append(r)

            output = [f"Found neighbor nodes for '{instance_name}':\n"]
            for dist in sorted(by_distance.keys()):
                dist_label = f"Within {dist} hops" if dist > 1 else "Direct neighbors"
                output.append(f"[{dist_label}]")
                for r in by_distance[dist][:10]:
                    name = r.get("name", "N/A")
                    db_id = r.get("id", "N/A")
                    labels = (
                        r.get("labels", ["Unknown"])[0]
                        if r.get("labels")
                        else "Unknown"
                    )
                    rels_info = []
                    for rel in r.get("relationships", []):
                        if dist > 1:
                            rels_info.append(f"from {rel['source']} via {rel['type']}")
                        else:
                            rels_info.append(f"{rel['type']}")

                    rel_str = ", ".join(rels_info)
                    output.append(
                        f"  - ID: {db_id}, Name: {name} (Type: {labels}, Relationship: {rel_str})"
                    )
                if len(by_distance[dist]) > 10:
                    output.append(f"  ... and {len(by_distance[dist]) - 10} more")
                output.append("")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def find_path_between_instances(
        start_name: str, end_name: str, max_depth: int = 5
    ) -> str:
        """Find the path between two instances."""

        async def _execute(tools) -> str:
            kwargs = {"max_depth": max_depth}
            if start_name.isdigit():
                kwargs["start_id"] = int(start_name)
            else:
                kwargs["start_name"] = start_name

            if end_name.isdigit():
                kwargs["end_id"] = int(end_name)
            else:
                kwargs["end_name"] = end_name

            result = await tools.find_path_between_instances(**kwargs)
            if not result:
                return f"No path found between '{start_name}' and '{end_name}'"
            nodes = result.get("nodes", [])
            rels = result.get("relationships", [])
            output = [f"Found path from '{start_name}' to '{end_name}':\n"]
            for i, node in enumerate(nodes):
                output.append(
                    f"  {i+1}. ID: {node.get('id', 'N/A')}, Name: {node['name']} ({node['labels'][0] if node['labels'] else 'Unknown'})"
                )
            output.append("\nRelationships:")
            for rel in rels:
                output.append(
                    f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}"
                )
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def describe_class(class_name: str) -> str:
        """Describe a class definition."""

        async def _execute(tools) -> str:
            result = await tools.describe_class(class_name)
            if "error" in result:
                return result["error"]
            class_info = result.get("class", {})
            output = [f"Class definition: {class_info.get('name', 'N/A')}\n"]
            output.append(f"Label: {class_info.get('label', 'N/A')}")
            props = class_info.get("dataProperties", [])
            if props:
                output.append("\nProperties:")
                for prop in props:
                    output.append(f"  - {prop}")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_ontology_classes() -> str:
        """Get all class definitions in the knowledge graph."""

        async def _execute(tools) -> str:
            results = await tools.get_ontology_classes()
            if not results:
                return "No class definitions found"
            output = [f"The knowledge graph defines {len(results)} classes:\n"]
            for r in results:
                name = r.get("name", "N/A")
                label = r.get("label", "N/A")
                output.append(f"  - {name} ({label})")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_ontology_relationships() -> str:
        """Get relationship definitions in the knowledge graph."""

        async def _execute(tools) -> str:
            results = await tools.get_ontology_relationships()
            if not results:
                return "No relationship definitions found"
            output = [
                f"The knowledge graph defines {len(results)} types of relationships:\n"
            ]
            for r in results:
                source = r.get("source", "N/A")
                rel_type = r.get("type", "N/A")
                target = r.get("target", "N/A")
                output.append(f"  - {source} --[{rel_type}]--> {target}")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_node_statistics(node_label: str | None = None) -> str:
        """Get node statistics."""

        async def _execute(tools) -> str:
            result = await tools.get_node_statistics(node_label)
            if node_label:
                total = result.get("total_count", 0)
                return f"Type '{node_label}' has a total of {total} instances."
            else:
                dist = result.get("label_distribution", [])
                output = ["Node type distribution:\n"]
                for d in dist:
                    label = (
                        d.get("labels", ["Unknown"])[0]
                        if d.get("labels")
                        else "Unknown"
                    )
                    count = d.get("count", 0)
                    output.append(f"  - {label}: {count}")
                return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    return [
        StructuredTool.from_function(
            coroutine=search_instances,
            name="search_instances",
            description="Search for entity instances in the knowledge graph by name, ID, or keyword.",
            args_schema=SearchInstancesInput,
        ),
        StructuredTool.from_function(
            coroutine=get_instances_by_class,
            name="get_instances_by_class",
            description="Get all instances of a specified type. Can be filtered by conditions.",
            args_schema=GetInstancesByClassInput,
        ),
        StructuredTool.from_function(
            coroutine=get_instance_neighbors,
            name="get_instance_neighbors",
            description="Query neighbor nodes of an instance to see which entities are related to it.",
            args_schema=GetInstanceNeighborsInput,
        ),
        StructuredTool.from_function(
            coroutine=find_path_between_instances,
            name="find_path_between_instances",
            description="Find the relationship path between two instances.",
            args_schema=FindPathInput,
        ),
        StructuredTool.from_function(
            coroutine=describe_class,
            name="describe_class",
            description="Describe a class definition, including properties and relationships.",
            args_schema=DescribeClassInput,
        ),
        StructuredTool.from_function(
            coroutine=get_ontology_classes,
            name="get_ontology_classes",
            description="Get all class definitions in the knowledge graph.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            coroutine=get_ontology_relationships,
            name="get_ontology_relationships",
            description="Get relationship definitions in the knowledge graph.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            coroutine=get_node_statistics,
            name="get_node_statistics",
            description="Get node statistics to understand data distribution.",
            args_schema=GetNodeStatisticsInput,
        ),
    ]


class QueryToolRegistry:
    """Registry for query tools."""

    def __init__(self, get_session_func: Callable[[], Any], event_emitter: Any = None):
        self.get_session_func = get_session_func
        self.event_emitter = event_emitter
        self._tools: list[StructuredTool] | None = None

    @property
    def tools(self) -> list[StructuredTool]:
        if self._tools is None:
            self._tools = create_query_tools(self.get_session_func, self.event_emitter)
        return self._tools

    def get_tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]
