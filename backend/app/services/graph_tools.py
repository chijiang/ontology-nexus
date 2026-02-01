# backend/app/services/graph_tools.py
from typing import List, Any
from neo4j import AsyncSession
from langchain_core.tools import tool


class GraphTools:
    """Neo4j 图查询工具集

    分为两层查询:
    - Ontology: 查询类定义和关系定义 (__Schema 标签)
    - Instance: 查询实际数据
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Ontology 查询 ====================

    async def get_ontology_classes(self) -> List[dict]:
        """获取所有类定义"""
        query = """
            MATCH (c:Class:__Schema)
            RETURN c.name as name, c.label as label, c.dataProperties as dataProperties
        """
        result = await self.session.run(query)
        return await result.data()

    async def get_ontology_relationships(self) -> List[dict]:
        """获取所有关系定义 (类之间的关系)"""
        query = """
            MATCH (c1:Class:__Schema)-[r]->(c2:Class:__Schema)
            RETURN c1.name as source_class, type(r) as relationship, c2.name as target_class
        """
        result = await self.session.run(query)
        return await result.data()

    async def describe_class(self, class_name: str) -> dict:
        """描述一个类的定义"""
        # 获取类信息
        class_query = """
            MATCH (c:Class:__Schema {name: $name})
            RETURN c.name as name, c.label as label, c.dataProperties as dataProperties
        """
        class_result = await self.session.run(class_query, name=class_name)
        class_data = await class_result.data()

        if not class_data:
            return {"error": f"Class '{class_name}' not found"}

        # 获取该类的关系
        rels_query = """
            MATCH (c:Class:__Schema {name: $name})-[r]->(target:Class:__Schema)
            RETURN type(r) as relationship, target.name as target_class
            UNION
            MATCH (source:Class:__Schema)-[r]->(c:Class:__Schema {name: $name})
            RETURN type(r) as relationship, source.name as source_class
        """
        rels_result = await self.session.run(rels_query, name=class_name)
        rels_data = await rels_result.data()

        return {"class": class_data[0], "relationships": rels_data}

    # ==================== Instance 查询 ====================

    async def search_instances(
        self, search_term: str, class_name: str | None = None, limit: int = 10
    ) -> List[dict]:
        """根据名称搜索实例节点"""
        if class_name:
            query = f"""
                MATCH (n:`{class_name}`)
                WHERE n.name CONTAINS $term AND n.__is_instance = true
                RETURN n.name AS name, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
            """
        else:
            query = """
                MATCH (n)
                WHERE n.name CONTAINS $term AND n.__is_instance = true
                RETURN n.name AS name, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
            """

        result = await self.session.run(query, term=search_term, limit=limit)
        data = await result.data()

        # 清理属性，移除内部字段
        for item in data:
            if "properties" in item:
                props = item["properties"]
                item["properties"] = {
                    k: v for k, v in props.items() if not k.startswith("__")
                }
        return data

    async def get_instance_neighbors(
        self,
        instance_name: str,
        hops: int = 1,
        direction: str = "both",
    ) -> List[dict]:
        """查询实例节点的邻居"""
        if direction == "outgoing":
            rel_pattern = f"-[r*1..{hops}]->"
        elif direction == "incoming":
            rel_pattern = f"<-[r*1..{hops}]-"
        else:
            rel_pattern = f"-[r*1..{hops}]-"

        query = f"""
            MATCH path = (start){rel_pattern}(neighbor)
            WHERE start.name = $name AND start.__is_instance = true
            RETURN DISTINCT neighbor.name AS name, labels(neighbor) AS labels,
                   [rel IN relationships(path) | type(rel)] AS relationships
            LIMIT 50
        """

        result = await self.session.run(query, name=instance_name)
        return await result.data()

    async def find_path_between_instances(
        self,
        start_name: str,
        end_name: str,
        max_depth: int = 5,
    ) -> dict | None:
        """查找两个实例之间的路径"""
        query = f"""
            MATCH path = shortestPath(
                (start {{name: $start}})-[*1..{max_depth}]-(end {{name: $end}})
            )
            WHERE start.__is_instance = true AND end.__is_instance = true
            RETURN [node IN nodes(path) | {{name: node.name, labels: labels(node)}}] AS nodes,
                   [rel IN relationships(path) | {{type: type(rel), source: startNode(rel).name, target: endNode(rel).name}}] AS relationships
        """

        result = await self.session.run(query, start=start_name, end=end_name)
        data = await result.data()
        return data[0] if data else None

    async def get_instances_by_class(
        self, class_name: str, filters: dict[str, Any] | None = None, limit: int = 20
    ) -> List[dict]:
        """获取某个类的所有实例"""
        conditions = ["n.__is_instance = true"]
        params = {"limit": limit}

        if filters:
            for key, value in filters.items():
                conditions.append(f"n.{key} = ${key}")
                params[key] = value

        where_clause = " AND ".join(conditions)

        query = f"""
            MATCH (n:`{class_name}`)
            WHERE {where_clause}
            RETURN n.name AS name, properties(n) AS properties
            LIMIT $limit
        """

        result = await self.session.run(query, **params)
        data = await result.data()

        # 清理属性
        for item in data:
            if "properties" in item:
                props = item["properties"]
                item["properties"] = {
                    k: v for k, v in props.items() if not k.startswith("__")
                }
        return data

    # ==================== 统计查询 ====================

    async def get_node_statistics(self, node_label: str | None = None) -> dict:
        """获取节点统计信息"""
        if node_label:
            query = f"""
                MATCH (n:{node_label})
                WHERE n.__is_instance = true
                RETURN count(n) AS total_count,
                       [d IN collect(n.name) | d][0..5] AS sample_names
            """
        else:
            query = """
                MATCH (n)
                WHERE NOT n:__Schema
                RETURN labels(n) AS labels, count(n) AS count
                ORDER BY count DESC
                LIMIT 20
            """

        result = await self.session.run(query)
        if node_label:
            data = (await result.data())[0]
            return {
                "total_count": data["total_count"],
                "sample_names": data["sample_names"],
            }
        else:
            return {"label_distribution": await result.data()}

    async def get_relationship_statistics(self) -> List[dict]:
        """获取关系类型统计"""
        query = """
            MATCH ()-[r]->()
            WHERE NOT startNode(r):__Schema
            RETURN type(r) AS relationship_type, count(r) AS count
            ORDER BY count DESC
            LIMIT 50
        """

        result = await self.session.run(query)
        return await result.data()


# LangChain 工具定义
def create_langchain_tools(get_session_func):
    """创建 LangChain 工具"""

    @tool
    async def get_ontology_classes() -> str:
        """获取知识图谱的类定义 (Ontology)。

        用于了解图谱中有哪些类型的实体。

        Returns:
            类定义列表，包含类名、描述和数据属性
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_ontology_classes()
            return f"图谱定义了 {len(results)} 个类: " + str(results)

    @tool
    async def get_ontology_relationships() -> str:
        """获取知识图谱的关系定义 (Ontology)。

        用于了解类之间可以有哪些关系。

        Returns:
            关系定义列表，包含源类、关系类型和目标类
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_ontology_relationships()
            return f"图谱定义了 {len(results)} 种关系: " + str(results)

    @tool
    async def describe_class(class_name: str) -> str:
        """描述一个类的定义，包括其属性和关系。

        Args:
            class_name: 类名，如 PurchaseOrder, Supplier 等

        Returns:
            类的详细定义
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.describe_class(class_name)
            return f"类定义: {result}"

    @tool
    async def search_instances(
        search_term: str, class_name: str | None = None, limit: int = 10
    ) -> str:
        """搜索实例数据。

        Args:
            search_term: 搜索关键词，如订单号、供应商名称等
            class_name: 可选，限制搜索的类型
            limit: 返回结果数量，默认10

        Returns:
            匹配的实例列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.search_instances(search_term, class_name, limit)
            return f"找到 {len(results)} 个实例: " + str(results)

    @tool
    async def get_instance_neighbors(
        instance_name: str, hops: int = 1, direction: str = "both"
    ) -> str:
        """查询实例的邻居节点。

        Args:
            instance_name: 实例名称，如 PO_2024_001
            hops: 跳数，默认1
            direction: 方向 (outgoing/incoming/both)，默认both

        Returns:
            邻居节点列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_instance_neighbors(instance_name, hops, direction)
            return f"找到 {len(results)} 个邻居: " + str(results)

    @tool
    async def find_path_between_instances(
        start_name: str, end_name: str, max_depth: int = 5
    ) -> str:
        """查找两个实例之间的路径。

        Args:
            start_name: 起始实例名称
            end_name: 目标实例名称
            max_depth: 最大深度，默认5

        Returns:
            路径信息（节点和关系）
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            result = await tools.find_path_between_instances(
                start_name, end_name, max_depth
            )
            if result:
                return f"找到路径: {result}"
            return "未找到路径"

    @tool
    async def get_instances_by_class(class_name: str, limit: int = 20) -> str:
        """获取某个类的所有实例。

        Args:
            class_name: 类名，如 PurchaseOrder
            limit: 返回数量，默认20

        Returns:
            实例列表
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_instances_by_class(class_name, None, limit)
            return f"找到 {len(results)} 个 {class_name} 实例: " + str(results)

    @tool
    async def get_node_statistics(node_label: str | None = None) -> str:
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
    async def get_relationship_statistics() -> str:
        """获取关系类型统计信息。

        Returns:
            关系类型及其数量
        """
        async with await get_session_func() as session:
            tools = GraphTools(session)
            results = await tools.get_relationship_statistics()
            return f"关系统计: {results}"

    return [
        get_ontology_classes,
        get_ontology_relationships,
        describe_class,
        search_instances,
        get_instance_neighbors,
        find_path_between_instances,
        get_instances_by_class,
        get_node_statistics,
        get_relationship_statistics,
    ]
