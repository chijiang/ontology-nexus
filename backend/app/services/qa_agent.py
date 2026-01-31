# backend/app/services/qa_agent.py
from typing import AsyncIterator
import json
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from app.services.schema_matcher import SchemaMatcher
from app.services.graph_tools import GraphTools, create_langchain_tools
from app.core.neo4j_pool import get_neo4j_driver


class QAAgent:
    """知识图谱问答 Agent"""

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
            match_result = await matcher.match_entities(query)
            yield {"type": "thinking", "content": f"识别实体: {list(match_result['entities'].keys())}"}

            # 2. 创建工具
            async def get_session():
                return driver.session(database=self.neo4j_config["database"])

            tools = create_langchain_tools(get_session)

            # 3. 创建 Agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个知识图谱问答助手。用户会问你关于知识图谱的问题。

你需要：
1. 理解用户问题的意图
2. 使用可用的工具查询图谱
3. 基于查询结果回答用户问题

不要编造数据，如果工具找不到结果，如实告诉用户。"""),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])

            agent = create_openai_functions_agent(self.llm, tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                return_intermediate_steps=True
            )

            # 4. 执行查询并流式返回
            yield {"type": "content_start"}

            async for chunk in executor.astream({"input": query}):
                if "output" in chunk:
                    yield {"type": "content", "content": chunk["output"]}
                elif "intermediate_steps" in chunk:
                    for step in chunk["intermediate_steps"]:
                        if hasattr(step[0], "tool"):
                            yield {"type": "tool_used", "tool": step[0].tool, "input": step[0].tool_input}
