# backend/app/services/qa_agent.py
from typing import AsyncIterator
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.schema_matcher import SchemaMatcher
from app.services.graph_tools import GraphTools
from app.core.neo4j_pool import get_neo4j_driver


class QAAgent:
    """知识图谱问答 Agent - 支持 Ontology 和 Instance 查询"""

    def __init__(self, user_id: int, db_session, llm_config: dict, neo4j_config: dict):
        self.user_id = user_id
        self.db_session = db_session
        self.llm_config = llm_config
        self.neo4j_config = neo4j_config

        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0,
        )

    def _detect_query_type(self, query: str, llm_entities: dict) -> str:
        """判断查询类型: ontology (概念/定义) 或 instance (具体数据)"""
        # 关键词匹配
        ontology_keywords = [
            "什么是",
            "定义",
            "概念",
            "类型",
            "有哪些类",
            "关系是什么",
            "可以有什么",
            "属性",
            "结构",
            "模型",
            "schema",
            "本体",
            "之间.*关系",
            "怎么关联",
            "如何连接",
            "子类",
            "父类",
            "包含哪些",
            "由什么组成",
            "有什么属性",
        ]

        instance_keywords = [
            r"[A-Z]+[_-]\d+",  # ID 模式
            "多少",
            "具体",
            "实例",
            "数据",
            "哪个",
            "谁",
            "什么时候",
            "创建",
            "订单",
            "发票",
        ]

        query_lower = query.lower()

        # 检查是否有具体 ID
        has_id = bool(re.search(r"[A-Z]+[_-]\d+[_-]?\d*", query))
        if has_id:
            return "instance"

        # 检查 ontology 关键词
        for keyword in ontology_keywords:
            if re.search(keyword, query):
                return "ontology"

        # 检查 LLM 的判断
        query_type = llm_entities.get("query_type", "instance")
        if query_type == "ontology":
            return "ontology"

        # 默认按 instance 查询
        return "instance"

    async def _query_ontology(
        self, tools: GraphTools, detected_classes: list, query: str
    ) -> tuple:
        """查询 Ontology（类定义和关系）"""
        graph_nodes = []
        graph_edges = []
        query_results = []
        seen_nodes = set()

        print(f"[DEBUG] Querying ontology for classes: {detected_classes}")

        # 获取所有类定义
        all_classes = await tools.get_ontology_classes()
        class_names = [c["name"] for c in all_classes]

        # 获取所有关系定义
        all_relationships = await tools.get_ontology_relationships()

        # 如果用户提到了特定类，则重点显示这些类
        if detected_classes:
            target_classes = [c for c in detected_classes if c in class_names]
            if not target_classes:
                # 模糊匹配
                for dc in detected_classes:
                    for cn in class_names:
                        if dc.lower() in cn.lower() or cn.lower() in dc.lower():
                            target_classes.append(cn)
        else:
            # 显示所有主要类
            target_classes = class_names[:10]

        # 添加类节点
        for cls in all_classes:
            if cls["name"] in target_classes:
                node_id = f"class:{cls['name']}"
                if node_id not in seen_nodes:
                    graph_nodes.append(
                        {"id": node_id, "label": cls["name"], "type": "Class"}
                    )
                    seen_nodes.add(node_id)
                    props = cls.get("dataProperties") or []
                    query_results.append(f"- 类 {cls['name']}: 属性 {props}")

        # 添加类之间的关系
        for rel in all_relationships:
            source_class = rel.get("source_class", "")
            target_class = rel.get("target_class", "")
            rel_name = rel.get("relationship", "")

            # 如果源或目标在目标类中
            if source_class in target_classes or target_class in target_classes:
                source_id = f"class:{source_class}"
                target_id = f"class:{target_class}"

                # 确保两端节点都存在
                if source_id not in seen_nodes:
                    graph_nodes.append(
                        {"id": source_id, "label": source_class, "type": "Class"}
                    )
                    seen_nodes.add(source_id)

                if target_id not in seen_nodes:
                    graph_nodes.append(
                        {"id": target_id, "label": target_class, "type": "Class"}
                    )
                    seen_nodes.add(target_id)

                graph_edges.append(
                    {"source": source_id, "target": target_id, "label": rel_name}
                )
                query_results.append(
                    f"- {source_class} --[{rel_name}]--> {target_class}"
                )

        return graph_nodes, graph_edges, query_results

    async def _query_instances(
        self, tools: GraphTools, instance_names: list, detected_classes: list
    ) -> tuple:
        """查询 Instance（具体数据）"""
        graph_nodes = []
        graph_edges = []
        query_results = []
        seen_nodes = set()

        print(f"[DEBUG] Querying instances: {instance_names}")

        # 搜索具体实例
        for instance_name in instance_names:
            try:
                results = await tools.search_instances(instance_name, limit=5)
                print(f"[DEBUG] Search results for {instance_name}: {results}")
                for r in results:
                    node_name = r.get("name")
                    if node_name and node_name not in seen_nodes:
                        node_type = (
                            r.get("labels", ["Unknown"])[0]
                            if r.get("labels")
                            else "Unknown"
                        )
                        props = r.get("properties", {})
                        graph_nodes.append(
                            {
                                "id": node_name,
                                "label": node_name,
                                "type": node_type,
                                "properties": props,
                            }
                        )
                        seen_nodes.add(node_name)
                        query_results.append(
                            f"- {node_name} (类型: {node_type}, 属性: {props})"
                        )
            except Exception as e:
                query_results.append(f"查询 {instance_name} 时出错: {str(e)}")

        # 如果没有找到具体实例，尝试按类搜索
        if not graph_nodes and detected_classes:
            for class_name in detected_classes[:2]:
                try:
                    results = await tools.get_instances_by_class(class_name, limit=5)
                    for r in results:
                        node_name = r.get("name")
                        if node_name and node_name not in seen_nodes:
                            props = r.get("properties", {})
                            graph_nodes.append(
                                {
                                    "id": node_name,
                                    "label": node_name,
                                    "type": class_name,
                                    "properties": props,
                                }
                            )
                            seen_nodes.add(node_name)
                            query_results.append(
                                f"- {node_name} (类型: {class_name}, 属性: {props})"
                            )
                except Exception:
                    pass

        # 查询相关关系
        for node in list(graph_nodes)[:3]:
            try:
                neighbors = await tools.get_instance_neighbors(node["id"], hops=1)
                for n in neighbors:
                    neighbor_name = n.get("name")
                    if neighbor_name and neighbor_name not in seen_nodes:
                        neighbor_type = (
                            n.get("labels", ["Unknown"])[0]
                            if n.get("labels")
                            else "Unknown"
                        )
                        neighbor_props = n.get("properties", {})
                        graph_nodes.append(
                            {
                                "id": neighbor_name,
                                "label": neighbor_name,
                                "type": neighbor_type,
                                "properties": neighbor_props,
                            }
                        )
                        seen_nodes.add(neighbor_name)
                        query_results.append(
                            f"- {neighbor_name} (类型: {neighbor_type}, 属性: {neighbor_props})"
                        )

                        for rel in n.get("relationships", []):
                            rel_label = rel["type"] if isinstance(rel, dict) else rel
                            graph_edges.append(
                                {
                                    "source": node["id"],
                                    "target": neighbor_name,
                                    "label": rel_label,
                                }
                            )
            except Exception:
                pass

        return graph_nodes, graph_edges, query_results

    async def astream_chat(self, query: str) -> AsyncIterator[dict]:
        """流式聊天"""
        yield {"type": "thinking", "content": "正在分析问题..."}

        driver = await get_neo4j_driver(**self.neo4j_config)
        async with driver.session(database=self.neo4j_config["database"]) as session:
            # 1. Schema 匹配
            matcher = SchemaMatcher(session, self.llm_config, self.neo4j_config)
            await matcher.initialize()
            match_result = await matcher.match_entities(query)

            entities_list = list(match_result.get("entities", {}).keys())
            llm_entities = match_result.get("llm_entities", {})

            # 2. 判断查询类型
            query_type = self._detect_query_type(query, llm_entities)
            yield {
                "type": "thinking",
                "content": f"识别实体: {entities_list}, 查询类型: {query_type}",
            }
            print(f"[DEBUG] Query type: {query_type}")

            tools = GraphTools(session)

            # 3. 根据查询类型执行不同的查询
            if query_type == "ontology":
                # 查询 Ontology
                detected_classes = llm_entities.get("detected_classes", [])
                graph_nodes, graph_edges, query_results = await self._query_ontology(
                    tools, detected_classes, query
                )
            else:
                # 查询 Instance
                instance_names = llm_entities.get("detected_instance_names", [])
                detected_classes = llm_entities.get("detected_classes", [])

                # 直接从查询中提取 ID 模式
                regex_instances = re.findall(r"[A-Z]+[_-]\d+[_-]?\d*", query)
                all_instance_names = list(set(instance_names + regex_instances))

                graph_nodes, graph_edges, query_results = await self._query_instances(
                    tools, all_instance_names, detected_classes
                )

            # 4. 构建回答上下文
            context_parts = []
            if query_results:
                if query_type == "ontology":
                    context_parts.append(
                        "知识图谱本体结构：\n" + "\n".join(query_results)
                    )
                else:
                    context_parts.append(
                        "找到的相关实体：\n" + "\n".join(query_results)
                    )

            if graph_nodes:
                context_parts.append(
                    f"\n找到 {len(graph_nodes)} 个节点，{len(graph_edges)} 个关系。"
                )

            # 获取 Schema 信息作为上下文
            schema_summary = matcher.get_schema_summary()
            context_parts.append(
                f"\n可用类: {', '.join(schema_summary['classes'][:10])}"
            )
            context_parts.append(
                f"可用关系: {', '.join(schema_summary['relationships'][:10])}"
            )

            context = (
                "\n".join(context_parts) if context_parts else "未找到直接匹配的信息。"
            )

            # 5. 使用 LLM 生成最终回答
            if query_type == "ontology":
                system_prompt = """你是一个知识图谱问答助手。用户在询问业务概念和本体结构相关的问题。
根据提供的知识图谱本体信息回答用户问题。

本体查询结果：
{context}

请基于查询结果解释相关的业务概念、类定义和关系。如果查询结果为空，告诉用户没有找到相关定义。
不要编造数据。"""
            else:
                system_prompt = """你是一个知识图谱问答助手。根据提供的图谱查询结果回答用户问题。

查询结果：
{context}

请基于查询结果简洁地回答问题。如果查询结果为空，告诉用户没有找到相关信息。
不要编造数据。"""

            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", "{query}")]
            )

            chain = prompt | self.llm

            yield {"type": "content_start"}

            # 流式返回 LLM 回答
            async for chunk in chain.astream({"context": context, "query": query}):
                if hasattr(chunk, "content"):
                    yield {"type": "content", "content": chunk.content}

            # 6. 返回图数据
            print(f"[DEBUG] Final graph_nodes: {graph_nodes}")
            print(f"[DEBUG] Final graph_edges: {graph_edges}")
            if graph_nodes:
                yield {
                    "type": "graph_data",
                    "nodes": graph_nodes[:20],
                    "edges": graph_edges[:30],
                }

        yield {"type": "done"}
