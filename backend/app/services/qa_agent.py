# backend/app/services/qa_agent.py
from typing import AsyncIterator
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.schema_matcher import SchemaMatcher
from app.services.graph_tools import GraphTools
from app.core.neo4j_pool import get_neo4j_driver


class QAAgent:
    """知识图谱问答 Agent - 简化实现"""

    def __init__(self, user_id: int, db_session, llm_config: dict, neo4j_config: dict):
        self.user_id = user_id
        self.db_session = db_session
        self.llm_config = llm_config
        self.neo4j_config = neo4j_config

        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0
        )

    async def astream_chat(self, query: str) -> AsyncIterator[dict]:
        """流式聊天"""
        # 1. Schema 匹配
        yield {"type": "thinking", "content": "正在分析问题..."}
        driver = await get_neo4j_driver(**self.neo4j_config)
        async with driver.session(database=self.neo4j_config["database"]) as session:
            matcher = SchemaMatcher(session, self.llm_config, self.neo4j_config)
            await matcher.initialize()
            match_result = await matcher.match_entities(query)
            entities_list = list(match_result.get('entities', {}).keys())
            yield {"type": "thinking", "content": f"识别实体: {entities_list}"}

            # 2. 根据匹配结果查询图谱
            tools = GraphTools(session)
            graph_data = []
            query_results = []

            # 收集所有匹配的实体 URI
            for entity_key, entity_info in match_result.get('entities', {}).items():
                matched_name = entity_info.get('matched', '')
                if not matched_name:
                    continue

                # 模糊搜索实体
                try:
                    results = await tools.fuzzy_search_entities(matched_name, limit=5)
                    for r in results:
                        if r.get('uri'):
                            graph_data.append({
                                'id': r['uri'],
                                'label': r.get('name', r['uri'])
                            })
                            query_results.append(f"- {r.get('name')} ({r['uri']})")
                except Exception as e:
                    query_results.append(f"查询 {matched_name} 时出错: {str(e)}")

            # 3. 查询相关关系
            for entity in graph_data[:3]:  # 限制前3个实体
                try:
                    neighbors = await tools.query_n_hop_neighbors(entity['id'], hops=1)
                    for n in neighbors:
                        if n.get('uri') and n.get('uri') != entity['id']:
                            graph_data.append({
                                'id': n['uri'],
                                'label': n.get('name', n['uri'])
                            })
                            # 添加关系
                            if n.get('relationships'):
                                for rel in n.get('relationships', []):
                                    graph_data.append({
                                        'source': entity['id'],
                                        'target': n['uri'],
                                        'label': rel
                                    })
                except Exception:
                    pass

            # 4. 构建回答
            context_parts = []
            if query_results:
                context_parts.append("找到的相关实体：\n" + "\n".join(query_results))

            if graph_data:
                nodes = [g for g in graph_data if 'id' in g and 'source' not in g]
                edges = [g for g in graph_data if 'source' in g]
                context_parts.append(f"\n找到 {len(nodes)} 个节点，{len(edges)} 个关系。")

            context = "\n".join(context_parts) if context_parts else "未找到直接匹配的实体。"

            # 5. 使用 LLM 生成最终回答
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个知识图谱问答助手。根据提供的图谱查询结果回答用户问题。

查询结果：
{context}

请基于查询结果简洁地回答问题。如果查询结果为空，告诉用户没有找到相关信息。
不要编造数据。"""),
                ("human", "{query}")
            ])

            chain = prompt | self.llm

            yield {"type": "content_start"}

            # 流式返回 LLM 回答
            async for chunk in chain.astream({"context": context, "query": query}):
                if hasattr(chunk, 'content'):
                    yield {"type": "content", "content": chunk.content}

            # 6. 返回图数据
            if graph_data:
                nodes = []
                edges = []
                seen_uris = set()

                for item in graph_data:
                    if 'id' in item and 'source' not in item:
                        if item['id'] not in seen_uris:
                            nodes.append(item)
                            seen_uris.add(item['id'])
                    elif 'source' in item:
                        edges.append(item)

                yield {
                    "type": "graph_data",
                    "nodes": nodes[:20],  # 限制节点数量
                    "edges": edges[:30]
                }

        yield {"type": "done"}
