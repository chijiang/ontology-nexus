"""Query tools for the enhanced agent.

These tools wrap the PostgreSQL graph storage functionality into LangChain-compatible tools.
Neo4j has been removed in favor of PostgreSQL + SQL/PGQ.
"""

from typing import Any, Callable
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.pg_graph_storage import PGGraphStorage
from sqlalchemy.ext.asyncio import AsyncSession


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


async def _get_session(get_session_func: Callable) -> AsyncSession:
    """Get the database session from the session function."""
    return await get_session_func()


async def _execute_with_session(
    get_session_func: Callable,
    func: Callable,
) -> Any:
    """Execute a function with a PostgreSQL graph storage instance.

    Args:
        get_session_func: Function that returns a database session
        func: Function to execute with storage instance

    Returns:
        Result of the function
    """
    session = await _get_session(get_session_func)
    tools = PGGraphStorage(session)
    return await func(tools)


def create_query_tools(
    get_session_func: Callable[[], AsyncSession],
) -> list[StructuredTool]:
    """Create LangChain-compatible query tools.

    Args:
        get_session_func: Async function that returns a database session

    Returns:
        List of StructuredTool instances
    """

    async def search_instances(
        search_term: str,
        class_name: str | None = None,
        limit: int = 10
    ) -> str:
        """搜索知识图谱中的实体实例。

        当用户想要按名称、ID或关键词查找特定实体时使用此工具。

        Args:
            search_term: 搜索关键词
            class_name: 可选，限制搜索的类型
            limit: 返回结果数量

        Returns:
            匹配的实例列表及其属性
        """
        async def _execute(tools) -> str:
            results = await tools.search_instances(search_term, class_name, limit)

            if not results:
                return f"未找到匹配 '{search_term}' 的实例"

            output = [f"找到 {len(results)} 个匹配 '{search_term}' 的实例:\n"]
            for r in results[:10]:
                name = r.get("name", "N/A")
                labels = r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                props = r.get("properties", {})
                props_str = ", ".join([f"{k}={v}" for k, v in props.items() if not k.startswith("__")])
                output.append(f"  - {name} (类型: {labels}, {props_str})")

            if len(results) > 10:
                output.append(f"  ... 还有 {len(results) - 10} 个结果")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def get_instances_by_class(
        class_name: str,
        limit: int = 20
    ) -> str:
        """获取指定类型的所有实例（不包含过滤条件）。

        注意：如果需要按名称或ID搜索特定实例，请使用 search_instances 工具。
        如果需要按属性过滤，请在获取结果后手动筛选，或使用 search_instances 配合关键词。

        Args:
            class_name: 类名，如 PurchaseOrder, Supplier 等
            limit: 返回结果数量，默认20

        Returns:
            该类型的实例列表
        """
        async def _execute(tools) -> str:
            # 不传递 filters，使用 None
            results = await tools.get_instances_by_class(class_name, None, limit)

            if not results:
                return f"未找到类型为 '{class_name}' 的实例。提示：如果需要搜索特定实例，请使用 search_instances 工具。"

            output = [f"找到 {len(results)} 个 '{class_name}' 类型的实例:\n"]
            for r in results[:15]:
                name = r.get("name", "N/A")
                props = r.get("properties", {})
                props_str = ", ".join([f"{k}={v}" for k, v in props.items() if not k.startswith("__")])
                output.append(f"  - {name} ({props_str})")

            if len(results) > 15:
                output.append(f"  ... 还有 {len(results) - 15} 个结果")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def get_instance_neighbors(
        instance_name: str,
        hops: int = 1,
        direction: str = "both"
    ) -> str:
        """查询实例的邻居节点。

        当用户想要查看与某个实体相关的其他实体时使用此工具。

        Args:
            instance_name: 实例名称
            hops: 跳数
            direction: 方向

        Returns:
            邻居节点列表和关系
        """
        async def _execute(tools) -> str:
            results = await tools.get_instance_neighbors(instance_name, hops, direction)

            if not results:
                return f"未找到 '{instance_name}' 的邻居节点"

            output = [f"找到 {len(results)} 个 '{instance_name}' 的邻居:\n"]
            for r in results[:15]:
                name = r.get("name", "N/A")
                labels = r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                rels = r.get("relationships", [])
                rel_str = ", ".join([rel.get("type", "unknown") for rel in rels[:3]])
                output.append(f"  - {name} (类型: {labels}, 关系: {rel_str})")

            if len(results) > 15:
                output.append(f"  ... 还有 {len(results) - 15} 个结果")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def find_path_between_instances(
        start_name: str,
        end_name: str,
        max_depth: int = 5
    ) -> str:
        """查找两个实例之间的路径。

        当用户想要了解两个实体如何关联时使用此工具。

        Args:
            start_name: 起始实例名称
            end_name: 目标实例名称
            max_depth: 最大深度

        Returns:
            路径信息或未找到的消息
        """
        async def _execute(tools) -> str:
            result = await tools.find_path_between_instances(start_name, end_name, max_depth)

            if not result:
                return f"在深度 {max_depth} 内未找到 '{start_name}' 和 '{end_name}' 之间的路径"

            nodes = result.get("nodes", [])
            rels = result.get("relationships", [])

            output = [f"找到从 '{start_name}' 到 '{end_name}' 的路径:\n"]
            for i, node in enumerate(nodes):
                output.append(f"  {i+1}. {node['name']} ({node['labels'][0] if node['labels'] else 'Unknown'})")

            output.append("\n关系:")
            for rel in rels:
                output.append(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def describe_class(class_name: str) -> str:
        """描述一个类的定义。

        当用户想要了解某个实体类型的定义时使用此工具。

        Args:
            class_name: 类名

        Returns:
            类的详细定义
        """
        async def _execute(tools) -> str:
            result = await tools.describe_class(class_name)

            if "error" in result:
                return result["error"]

            class_info = result.get("class", {})
            relationships = result.get("relationships", [])

            output = [f"类定义: {class_info.get('name', 'N/A')}\n"]
            output.append(f"标签: {class_info.get('label', 'N/A')}")

            props = class_info.get("dataProperties", [])
            if props:
                output.append("\n属性:")
                for prop in props:
                    output.append(f"  - {prop}")

            if relationships:
                output.append("\n关系:")
                for rel in relationships:
                    rel_type = rel.get("relationship", "unknown")
                    target = rel.get("target_class") or rel.get("source_class", "unknown")
                    output.append(f"  - {rel_type} -> {target}")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def get_ontology_classes() -> str:
        """获取知识图谱的所有类定义。

        当用户想要了解图谱中有哪些类型的实体时使用此工具。

        Returns:
            所有类定义的列表
        """
        async def _execute(tools) -> str:
            results = await tools.get_ontology_classes()

            if not results:
                return "未找到类定义"

            output = [f"知识图谱定义了 {len(results)} 个类:\n"]
            for r in results:
                name = r.get("name", "N/A")
                label = r.get("label", "N/A")
                props = r.get("dataProperties", [])
                props_str = ", ".join(props) if props else "无"
                output.append(f"  - {name} ({label}): 属性 [{props_str}]")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def get_ontology_relationships() -> str:
        """获取知识图谱的关系定义。

        当用户想要了解类之间可以有哪些关系时使用此工具。

        Returns:
            所有关系定义的列表
        """
        async def _execute(tools) -> str:
            results = await tools.get_ontology_relationships()

            if not results:
                return "未找到关系定义"

            output = [f"知识图谱定义了 {len(results)} 种关系:\n"]
            for r in results:
                source = r.get("source_class", "N/A")
                rel_type = r.get("relationship", "N/A")
                target = r.get("target_class", "N/A")
                output.append(f"  - {source} --[{rel_type}]--> {target}")

            return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

    async def get_node_statistics(node_label: str | None = None) -> str:
        """获取节点统计信息。

        当用户想要了解数据的统计情况时使用此工具。

        Args:
            node_label: 可选，指定节点类型

        Returns:
            统计信息
        """
        async def _execute(tools) -> str:
            result = await tools.get_node_statistics(node_label)

            if node_label:
                total = result.get("total_count", 0)
                samples = result.get("sample_names", [])
                samples_str = ", ".join(samples) if samples else "无"
                return f"类型 '{node_label}' 共有 {total} 个实例。示例: {samples_str}"
            else:
                dist = result.get("label_distribution", [])
                output = ["节点类型分布:\n"]
                for d in dist:
                    label = d.get("labels", ["Unknown"])[0] if d.get("labels") else "Unknown"
                    count = d.get("count", 0)
                    output.append(f"  - {label}: {count}")
                return "\n".join(output)

        return await _execute_with_session(get_session_func, _execute)

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
            description="描述一个类的定义，包括属性和关系。",
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
    """Registry for query tools.

    This class manages the lifecycle of query tools and provides
    a convenient interface for tool creation and management.
    """

    def __init__(self, get_session_func: Callable[[], AsyncSession]):
        """Initialize the query tool registry.

        Args:
            get_session_func: Async function that returns a database session
        """
        self.get_session_func = get_session_func
        self._tools: list[StructuredTool] | None = None

    @property
    def tools(self) -> list[StructuredTool]:
        """Get the list of query tools."""
        if self._tools is None:
            self._tools = create_query_tools(self.get_session_func)
        return self._tools

    def get_tool_names(self) -> list[str]:
        """Get the names of all query tools."""
        return [tool.name for tool in self.tools]
