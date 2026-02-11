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

    search_term: str = Field(description="搜索关键词，如订单号、供应商名称等")
    class_name: str | None = Field(None, description="可选，限制搜索的实体类型")
    limit: int = Field(10, description="返回结果数量，默认10")


class GetInstancesByClassInput(BaseModel):
    """Input for get_instances_by_class tool."""

    class_name: str = Field(description="类名，如 PurchaseOrder, Supplier 等")
    limit: int = Field(20, description="返回结果数量，默认20")


class GetInstanceNeighborsInput(BaseModel):
    """Input for get_instance_neighbors tool."""

    instance_name: str = Field(description="实例名称，如 PO_2024_001")
    hops: int = Field(1, description="跳数，默认1")
    direction: str = Field("both", description="方向: outgoing, incoming, 或 both")
    type: str | None = Field(None, description="可选，指定查询的邻居类型")
    property_filter: Dict[str, Any] | None = Field(
        None, description="可选，过滤目标属性，如 {'status': 'Open'}"
    )


class FindPathInput(BaseModel):
    """Input for find_path_between_instances tool."""

    start_name: str = Field(description="起始实例名称")
    end_name: str = Field(description="目标实例名称")
    max_depth: int = Field(5, description="最大深度，默认5")


class DescribeClassInput(BaseModel):
    """Input for describe_class tool."""

    class_name: str = Field(description="类名，如 PurchaseOrder")


class GetNodeStatisticsInput(BaseModel):
    """Input for get_node_statistics tool."""

    node_label: str | None = Field(None, description="可选，指定节点类型进行统计")


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
        """搜索知识图谱中的实体实例。"""

        async def _execute(tools) -> str:
            results = await tools.search_instances(search_term, class_name, limit)
            if not results:
                return f"未找到匹配 '{search_term}' 的实例"
            output = [f"找到 {len(results)} 个匹配 '{search_term}' 的实例:\n"]
            for r in results[:10]:
                name = r.get("name", "N/A")
                labels = (
                    r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                )
                props = r.get("properties", {})
                props_str = ", ".join(
                    [f"{k}={v}" for k, v in props.items() if not k.startswith("__")]
                )
                output.append(f"  - {name} (类型: {labels}, {props_str})")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_instances_by_class(class_name: str, limit: int = 20) -> str:
        """获取指定类型的所有实例。"""

        async def _execute(tools) -> str:
            results = await tools.get_instances_by_class(class_name, None, limit)
            if not results:
                return f"未找到类型为 '{class_name}' 的实例。"
            output = [f"找到 {len(results)} 个 '{class_name}' 类型的实例:\n"]
            for r in results[:15]:
                name = r.get("name", "N/A")
                props = r.get("properties", {})
                props_str = ", ".join(
                    [f"{k}={v}" for k, v in props.items() if not k.startswith("__")]
                )
                output.append(f"  - {name} ({props_str})")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_instance_neighbors(
        instance_name: str,
        hops: int = 1,
        direction: str = "both",
        type: str | None = None,
        property_filter: Dict[str, Any] | None = None,
    ) -> str:
        """查询实例的邻居节点。"""

        async def _execute(tools) -> str:
            results = await tools.get_instance_neighbors(
                instance_name,
                hops,
                direction,
                entity_type=type,
                property_filter=property_filter,
            )
            if not results:
                return f"未找到 '{instance_name}' 的邻居节点"

            # Group by distance
            by_distance = {}
            for r in results:
                dist = r.get("distance", 1)
                if dist not in by_distance:
                    by_distance[dist] = []
                by_distance[dist].append(r)

            output = [f"找到 '{instance_name}' 的邻居节点:\n"]
            for dist in sorted(by_distance.keys()):
                dist_label = f"{dist}跳内" if dist > 1 else "直接邻居"
                output.append(f"【{dist_label}】")
                for r in by_distance[dist][:10]:
                    name = r.get("name", "N/A")
                    labels = (
                        r.get("labels", ["Unknown"])[0]
                        if r.get("labels")
                        else "Unknown"
                    )
                    rels_info = []
                    for rel in r.get("relationships", []):
                        if dist > 1:
                            rels_info.append(f"来自 {rel['source']} 的 {rel['type']}")
                        else:
                            rels_info.append(f"{rel['type']}")

                    rel_str = ", ".join(rels_info)
                    output.append(f"  - {name} (类型: {labels}, 关系: {rel_str})")
                if len(by_distance[dist]) > 10:
                    output.append(f"  ... 还有 {len(by_distance[dist]) - 10} 个")
                output.append("")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def find_path_between_instances(
        start_name: str, end_name: str, max_depth: int = 5
    ) -> str:
        """查找两个实例之间的路径。"""

        async def _execute(tools) -> str:
            result = await tools.find_path_between_instances(
                start_name, end_name, max_depth
            )
            if not result:
                return f"未找到 '{start_name}' 和 '{end_name}' 之间的路径"
            nodes = result.get("nodes", [])
            rels = result.get("relationships", [])
            output = [f"找到从 '{start_name}' 到 '{end_name}' 的路径:\n"]
            for i, node in enumerate(nodes):
                output.append(
                    f"  {i+1}. {node['name']} ({node['labels'][0] if node['labels'] else 'Unknown'})"
                )
            output.append("\n关系:")
            for rel in rels:
                output.append(
                    f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}"
                )
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def describe_class(class_name: str) -> str:
        """描述一个类的定义。"""

        async def _execute(tools) -> str:
            result = await tools.describe_class(class_name)
            if "error" in result:
                return result["error"]
            class_info = result.get("class", {})
            output = [f"类定义: {class_info.get('name', 'N/A')}\n"]
            output.append(f"标签: {class_info.get('label', 'N/A')}")
            props = class_info.get("dataProperties", [])
            if props:
                output.append("\n属性:")
                for prop in props:
                    output.append(f"  - {prop}")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_ontology_classes() -> str:
        """获取知识图谱的所有类定义。"""

        async def _execute(tools) -> str:
            results = await tools.get_ontology_classes()
            if not results:
                return "未找到类定义"
            output = [f"知识图谱定义了 {len(results)} 个类:\n"]
            for r in results:
                name = r.get("name", "N/A")
                label = r.get("label", "N/A")
                output.append(f"  - {name} ({label})")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_ontology_relationships() -> str:
        """获取知识图谱的关系定义。"""

        async def _execute(tools) -> str:
            results = await tools.get_ontology_relationships()
            if not results:
                return "未找到关系定义"
            output = [f"知识图谱定义了 {len(results)} 种关系:\n"]
            for r in results:
                source = r.get("source", "N/A")
                rel_type = r.get("type", "N/A")
                target = r.get("target", "N/A")
                output.append(f"  - {source} --[{rel_type}]--> {target}")
            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute, event_emitter)

    async def get_node_statistics(node_label: str | None = None) -> str:
        """获取节点统计信息。"""

        async def _execute(tools) -> str:
            result = await tools.get_node_statistics(node_label)
            if node_label:
                total = result.get("total_count", 0)
                return f"类型 '{node_label}' 共有 {total} 个实例。"
            else:
                dist = result.get("label_distribution", [])
                output = ["节点类型分布:\n"]
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
            description="搜索知识图谱中的实体实例。按名称、ID或关键词查找。",
            args_schema=SearchInstancesInput,
        ),
        StructuredTool.from_function(
            coroutine=get_instances_by_class,
            name="get_instances_by_class",
            description="获取指定类型的所有实例。可以按条件过滤。",
            args_schema=GetInstancesByClassInput,
        ),
        StructuredTool.from_function(
            coroutine=get_instance_neighbors,
            name="get_instance_neighbors",
            description="查询实例的邻居节点，了解哪些实体与它相关联。",
            args_schema=GetInstanceNeighborsInput,
        ),
        StructuredTool.from_function(
            coroutine=find_path_between_instances,
            name="find_path_between_instances",
            description="查找两个实例之间的关联路径。",
            args_schema=FindPathInput,
        ),
        StructuredTool.from_function(
            coroutine=describe_class,
            name="describe_class",
            description="描述一个类的定义，包括属性 and 关系。",
            args_schema=DescribeClassInput,
        ),
        StructuredTool.from_function(
            coroutine=get_ontology_classes,
            name="get_ontology_classes",
            description="获取知识图谱的所有类定义。",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            coroutine=get_ontology_relationships,
            name="get_ontology_relationships",
            description="获取知识图谱的关系定义。",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            coroutine=get_node_statistics,
            name="get_node_statistics",
            description="获取节点统计信息，了解数据分布。",
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
