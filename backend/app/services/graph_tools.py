# backend/app/services/graph_tools.py
from typing import List, Any
from neo4j import AsyncSession
from langchain_core.tools import tool


class GraphTools:
    """Neo4j 图查询工具集"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fuzzy_search_entities(
        self,
        search_term: str,
        node_label: str | None = None,
        limit: int = 10
    ) -> List[dict]:
        """根据实体名称模糊搜索节点"""
        if node_label:
            query = f"""
                MATCH (n:{node_label})
                WHERE n.name CONTAINS $term OR n.label CONTAINS $term
                RETURN n.uri AS uri, n.name AS name, labels(n) AS labels
                LIMIT $limit
            """
        else:
            query = """
                MATCH (n)
                WHERE n.name CONTAINS $term OR n.label CONTAINS $term
                RETURN n.uri AS uri, n.name AS name, labels(n) AS labels
                LIMIT $limit
            """

        result = await self.session.run(query, term=search_term, limit=limit)
        return [record.data() for record in await result.data()]

    async def fuzzy_search_relationships(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[dict]:
        """根据关系名称模糊搜索关系类型"""
        query = """
            MATCH ()-[r]->()
            WHERE type(r) CONTAINS $term
            RETURN DISTINCT type(r) AS relationship_type, count(r) AS count
            ORDER BY count DESC
            LIMIT $limit
        """

        result = await self.session.run(query, term=search_term, limit=limit)
        return [record.data() for record in await result.data()]

    async def query_n_hop_neighbors(
        self,
        node_uri: str,
        hops: int = 1,
        direction: str = "both",
        relationship_types: List[str] | None = None
    ) -> List[dict]:
        """查询节点的 N 跳邻居"""
        rel_pattern = ""
        if relationship_types:
            rels = "|".join(relationship_types)
            if direction == "outgoing":
                rel_pattern = f"[r:{rels}]"
            elif direction == "incoming":
                rel_pattern = f"[r:{rels}]"
            else:
                rel_pattern = f"[r:{rels}]"
        else:
            if direction == "outgoing":
                rel_pattern = "[r]->"
            elif direction == "incoming":
                rel_pattern = "[r<-]"
            else:
                rel_pattern = "[r]"

        query = f"""
            MATCH path = (start {{uri: $uri}})-{rel_pattern}*{hops}..{hops}(neighbor)
            RETURN DISTINCT neighbor.uri AS uri, neighbor.name AS name,
                   labels(neighbor) AS labels, [r IN relationships(path) | type(r)] AS relationships
            LIMIT 100
        """

        result = await self.session.run(query, uri=node_uri)
        return [record.data() for record in await result.data()]

    async def find_path_between_nodes(
        self,
        start_uri: str,
        end_uri: str,
        max_depth: int = 5,
        relationship_types: List[str] | None = None
    ) -> List[dict]:
        """查找两个节点之间的路径"""
        rel_pattern = ""
        if relationship_types:
            rels = "|".join(relationship_types)
            rel_pattern = f":{rels}"

        query = f"""
            MATCH path = shortestPath(
                (start {{uri: $start}})-[*1..{max_depth}{rel_pattern}]-(end {{uri: $end}})
            )
            RETURN [node IN nodes(path) | {{uri: node.uri, name: node.name, labels: labels(node)}}] AS nodes,
                   [rel IN relationships(path) | {{type: type(rel), source: startNode(rel).uri, target: endNode(rel).uri}}] AS relationships
        """

        result = await self.session.run(query, start=start_uri, end=end_uri)
        data = await result.data()
        return data[0] if data else None

    async def query_nodes_by_filters(
        self,
        node_label: str,
        filters: dict[str, Any]
    ) -> List[dict]:
        """根据属性条件过滤节点"""
        conditions = []
        params = {"label": node_label}

        for key, value in filters.items():
            conditions.append(f"n.{key} = ${key}")
            params[key] = value

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
            MATCH (n:{node_label})
            WHERE {where_clause}
            RETURN n.uri AS uri, n.name AS name, n AS properties
            LIMIT 100
        """

        result = await self.session.run(query, **params)
        return [record.data() for record in await result.data()]

    async def get_node_statistics(
        self,
        node_label: str | None = None
    ) -> dict:
        """获取节点统计信息"""
        if node_label:
            query = f"""
                MATCH (n:{node_label})
                RETURN count(n) AS total_count,
                       [d IN collect(n.name) | d][0..5] AS sample_names
            """
        else:
            query = """
                MATCH (n)
                RETURN labels(n) AS labels, count(n) AS count
                ORDER BY count DESC
                LIMIT 20
            """

        result = await self.session.run(query)
        if node_label:
            data = (await result.data())[0]
            return {"total_count": data["total_count"], "sample_names": data["sample_names"]}
        else:
            return {"label_distribution": [record.data() for record in await result.data()]}

    async def get_relationship_types(
        self,
        node_label: str | None = None
    ) -> List[dict]:
        """获取可用的关系类型及其使用频率"""
        if node_label:
            query = f"""
                MATCH (:{node_label})-[r]->()
                RETURN type(r) AS relationship_type, count(r) AS count
                ORDER BY count DESC
            """
        else:
            query = """
                MATCH ()-[r]->()
                RETURN type(r) AS relationship_type, count(r) AS count
                ORDER BY count DESC
                LIMIT 50
            """

        result = await self.session.run(query)
        return [record.data() for record in await result.data()]


# LangChain 工具定义
def create_langchain_tools(get_session_func):
    """创建 LangChain 工具"""

    @tool
    async def fuzzy_search_entities(
        search_term: str,
        node_label: str | None = None,
        limit: int = 10
    ) -> str:
        """根据实体名称模糊搜索节点。

        Args:
            search_term: 搜索关键词
            node_label: 可选，限制节点类型
            limit: 返回结果数量，默认10

        Returns:
            匹配的节点列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.fuzzy_search_entities(search_term, node_label, limit)
            return f"找到 {len(results)} 个匹配实体: " + str(results)

    @tool
    async def fuzzy_search_relationships(
        search_term: str,
        limit: int = 10
    ) -> str:
        """根据关系名称模糊搜索关系类型。

        Args:
            search_term: 搜索关键词
            limit: 返回结果数量，默认10

        Returns:
            匹配的关系类型列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.fuzzy_search_relationships(search_term, limit)
            return f"找到 {len(results)} 种关系类型: " + str(results)

    @tool
    async def query_n_hop_neighbors(
        node_uri: str,
        hops: int = 1,
        direction: str = "both"
    ) -> str:
        """查询节点的 N 跳邻居。

        Args:
            node_uri: 节点 URI
            hops: 跳数，默认1
            direction: 方向 (outgoing/incoming/both)，默认both

        Returns:
            邻居节点列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.query_n_hop_neighbors(node_uri, hops, direction)
            return f"找到 {len(results)} 个邻居: " + str(results)

    @tool
    async def find_path_between_nodes(
        start_uri: str,
        end_uri: str,
        max_depth: int = 5
    ) -> str:
        """查找两个节点之间的路径。

        Args:
            start_uri: 起始节点 URI
            end_uri: 目标节点 URI
            max_depth: 最大深度，默认5

        Returns:
            路径信息（节点和关系）
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.find_path_between_nodes(start_uri, end_uri, max_depth)
            if result:
                return f"找到路径: {result}"
            return "未找到路径"

    @tool
    async def query_nodes_by_filters(
        node_label: str,
        filters: str  # JSON string
    ) -> str:
        """根据属性条件过滤节点。

        Args:
            node_label: 节点类型
            filters: 过滤条件的 JSON 字符串，例如 '{"status": "active"}'

        Returns:
            匹配的节点列表
        """
        import json
        filter_dict = json.loads(filters)
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.query_nodes_by_filters(node_label, filter_dict)
            return f"找到 {len(results)} 个节点: " + str(results)

    @tool
    async def get_node_statistics(
        node_label: str | None = None
    ) -> str:
        """获取节点统计信息。

        Args:
            node_label: 可选，指定节点类型

        Returns:
            统计信息
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.get_node_statistics(node_label)
            return f"统计信息: {result}"

    @tool
    async def get_relationship_types(
        node_label: str | None = None
    ) -> str:
        """获取可用的关系类型及其使用频率。

        Args:
            node_label: 可选，限制节点的类型

        Returns:
            关系类型列表及使用频率
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_relationship_types(node_label)
            return f"关系类型: {results}"

    return [
        fuzzy_search_entities,
        fuzzy_search_relationships,
        query_n_hop_neighbors,
        find_path_between_nodes,
        query_nodes_by_filters,
        get_node_statistics,
        get_relationship_types,
    ]
