"""Enhanced Agent Service using LangGraph.

This is the main entry point for the enhanced agent functionality.
It combines LangGraph orchestration with query and action tools.
"""

import logging
import asyncio
from typing import Any, AsyncIterator, Callable, Optional
from langchain_openai import ChatOpenAI

from app.services.agent.state import AgentState, StreamEvent, UserIntent
from app.services.agent.graph import create_agent_graph
from app.services.agent_tools.query_tools import QueryToolRegistry
from app.services.agent_tools.action_tools import ActionToolRegistry

logger = logging.getLogger(__name__)


class EnhancedAgentService:
    """Enhanced QA Agent with query and action capabilities.

    This agent uses LangGraph for orchestration and supports:
    - Query tools for information retrieval
    - Action tools for executing operations
    - Batch concurrent execution with progress tracking
    - Streaming responses with real-time updates
    """

    def __init__(
        self,
        llm_config: dict[str, Any],
        neo4j_config: dict[str, Any] | None,
        action_executor: Any = None,
        action_registry: Any = None,
    ):
        """Initialize the enhanced agent service.

        Args:
            llm_config: LLM configuration dict with api_key, base_url, model
            neo4j_config: Deprecated - Neo4j has been replaced with PostgreSQL
            action_executor: Optional ActionExecutor instance for action execution
            action_registry: Optional ActionRegistry instance for looking up actions
        """
        self.llm_config = llm_config
        self.neo4j_config = neo4j_config  # Kept for compatibility, now unused
        self.action_executor = action_executor
        self.action_registry = action_registry

        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0,
        )

        # Initialize graph (lazy loading)
        self._graph = None

    def _get_session(self):
        """Get a database session context manager.

        Returns None since Neo4j has been removed.
        Query tools now use PostgreSQL directly.
        """
        return None

    def _get_graph(self):
        """Get or create the LangGraph."""
        if self._graph is None:
            # Create query tools registry
            query_registry = QueryToolRegistry(self._get_session)
            query_tools = query_registry.tools

            # Create action tools if action_executor and action_registry are available
            action_tools = []
            if self.action_executor and self.action_registry:
                action_registry = ActionToolRegistry(
                    self._get_session,
                    self.action_executor,
                    self.action_registry
                )
                action_tools = action_registry.tools

            # Create the graph without memory (conversation history is managed in database)
            self._graph = create_agent_graph(
                llm=self.llm,
                query_tools=query_tools,
                action_tools=action_tools,
                with_memory=False,  # Disable checkpointer since we manage history in database
            )

        return self._graph

    async def astream_chat(self, query: str) -> AsyncIterator[StreamEvent]:
        """Stream chat responses with real-time updates.

        This method yields events as the agent processes the request,
        including thinking, tool calls, and final results.

        Args:
            query: User's query or request

        Yields:
            StreamEvent objects with type and content
        """
        from langchain_core.messages import HumanMessage

        logger.info(f"=== Agent astream_chat started ===")
        logger.info(f"User query: {query}")

        # Initial thinking event
        yield {
            "type": "thinking",
            "content": "正在分析您的请求...",
        }

        # Get the graph
        graph = self._get_graph()
        action_count = len(self.action_registry._actions) if self.action_registry else 0
        logger.info(f"Graph created, actions in registry: {action_count}")

        # Create initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
        }

        # Track intent and step
        current_intent = None
        content_parts = []
        processed_messages = set()  # Track already processed messages

        try:
            # Stream the graph execution
            async for event in graph.astream(initial_state):
                # event format: {"node_name": {state_dict}}
                for node_name, node_state in event.items():
                    if node_state is None:
                        continue

                    logger.info(f"=== Node: {node_name} ===")

                    # Extract step information
                    step = node_state.get("current_step", "")
                    intent = node_state.get("user_intent", "")

                    if intent:
                        logger.info(f"Intent: {intent}")
                    if step:
                        logger.info(f"Step: {step}")

                    # Emit intent change
                    if intent and intent != current_intent:
                        current_intent = intent
                        intent_text = {
                            UserIntent.QUERY: "查询信息",
                            UserIntent.ACTION: "执行操作",
                            UserIntent.DIRECT_ANSWER: "回答问题",
                        }.get(intent, intent)

                        logger.info(f"Intent changed to: {intent_text}")
                        yield {
                            "type": "thinking",
                            "content": f"识别意图: {intent_text}",
                        }

                    # Process messages from the node
                    messages = node_state.get("messages", [])
                    logger.info(f"Messages in node: {len(messages)}")

                    for msg in messages:
                        msg_id = id(msg)

                        # Check for tool calls
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            logger.info(f"Tool calls detected: {len(msg.tool_calls)}")
                            for tc in msg.tool_calls:
                                logger.info(f"  - Tool: {tc.get('name')}, Args: {tc.get('args')}")

                        # Only process new AI messages
                        if hasattr(msg, "type") and msg.type == "ai":
                            content = msg.content or ""

                            if content and msg_id not in processed_messages:
                                processed_messages.add(msg_id)
                                logger.info(f"AI Message (length: {len(content)}): {content[:200]}...")

                                # Skip if it's just our placeholder
                                if "[注意：Action 执行功能将在 Phase 2 中实现]" in content:
                                    content = content.replace(
                                        "\n\n[注意：Action 执行功能将在 Phase 2 中实现]", ""
                                    )

                                if content:
                                    # For query results, stream the content
                                    yield {
                                        "type": "content",
                                        "content": content,
                                    }
                                    content_parts.append(content)

                        # Check for tool messages
                        if hasattr(msg, "type") and msg.type == "tool":
                            logger.info(f"Tool result: {msg.name[:50] if hasattr(msg, 'name') else 'unknown'}")
                            if msg.content:
                                logger.info(f"  Result: {str(msg.content)[:200]}...")

                    # Check for query results that might have graph data
                    query_results = node_state.get("query_results", [])
                    if query_results and current_intent == UserIntent.QUERY:
                        # Try to extract graph data from query results
                        graph_data = self._extract_graph_data(query_results)
                        if graph_data and (graph_data.get("nodes") or graph_data.get("edges")):
                            yield {
                                "type": "graph_data",
                                "nodes": graph_data.get("nodes", [])[:20],
                                "edges": graph_data.get("edges", [])[:30],
                            }

        except Exception as e:
            logger.error(f"Error in astream_chat: {e}", exc_info=True)
            yield {
                "type": "content",
                "content": f"\n\n抱歉，处理请求时发生错误: {str(e)}",
            }

        # Final done event
        yield {"type": "done"}

    def _extract_graph_data(self, query_results: list) -> dict | None:
        """Extract graph visualization data from query results.

        Args:
            query_results: List of query execution results

        Returns:
            Dict with nodes and edges for visualization
        """
        nodes = []
        edges = []
        seen_nodes = set()

        for step in query_results:
            if len(step) >= 2:
                tool_call, tool_result = step[0], step[1]

                # Parse tool result to extract entities
                result_str = str(tool_result)

                # Try to extract instances from the result
                # This is a simple heuristic - in production, you'd parse more carefully
                import re

                # Look for patterns like "PO_2024_001" or "Supplier_001"
                entity_pattern = r'\b[A-Z][a-zA-Z_]*[_-]\d+[_-]?\d*\b'
                entities = re.findall(entity_pattern, result_str)

                for entity in entities:
                    if entity not in seen_nodes:
                        seen_nodes.add(entity)
                        # Try to infer type from the entity name
                        entity_type = "Unknown"
                        for prefix in ["PO", "Invoice", "Supplier", "Customer"]:
                            if entity.startswith(prefix):
                                entity_type = prefix
                                break

                        nodes.append({
                            "id": entity,
                            "label": entity,
                            "type": entity_type,
                        })

                # Look for relationship patterns
                rel_pattern = r'(\w+)\s*--\[(\w+)\]\s*-->\s*(\w+)'
                relationships = re.findall(rel_pattern, result_str)

                for rel in relationships:
                    source, rel_type, target = rel
                    edges.append({
                        "source": source,
                        "target": target,
                        "label": rel_type,
                    })

        return {"nodes": nodes, "edges": edges} if nodes or edges else None

    async def ainvoke(self, query: str) -> AgentState:
        """Invoke the agent and return the final state.

        This is a non-streaming version of astream_chat.

        Args:
            query: User's query or request

        Returns:
            Final AgentState after execution
        """
        from langchain_core.messages import HumanMessage

        graph = self._get_graph()
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
        }

        result = await graph.ainvoke(initial_state)
        return result

    async def get_available_actions(self, entity_type: str) -> list[dict]:
        """Get available actions for an entity type.

        Args:
            entity_type: The entity type to query

        Returns:
            List of available action definitions
        """
        if self.action_registry is None:
            return []

        actions = self.action_registry.list_by_entity(entity_type)

        return [
            {
                "entity_type": action.entity_type,
                "action_name": action.action_name,
                "parameters": [
                    {"name": p.name, "type": p.param_type, "optional": p.optional}
                    for p in (action.parameters or [])
                ],
                "precondition_count": len(action.preconditions or []),
                "has_effect": action.effect is not None,
            }
            for action in actions
        ]

    async def validate_action(
        self,
        entity_type: str,
        action_name: str,
        entity_id: str,
    ) -> dict[str, Any]:
        """Validate if an action can be executed.

        Args:
            entity_type: The entity type
            action_name: The action name
            entity_id: The entity ID

        Returns:
            Validation result with can_execute and reasons
        """
        if not self.action_registry:
            return {
                "can_execute": False,
                "reason": "Action registry not configured",
            }

        action = self.action_registry.lookup(entity_type, action_name)
        if not action:
            return {
                "can_execute": False,
                "reason": f"Action {entity_type}.{action_name} not found",
            }

        # Check if entity exists using PostgreSQL
        from app.services.pg_graph_storage import PGGraphStorage
        from app.core.database import async_session

        async with async_session() as db:
            storage = PGGraphStorage(db)
            instances = await storage.search_instances(entity_id, entity_type, limit=1)

            if not instances:
                return {
                    "can_execute": False,
                    "reason": f"Entity {entity_id} not found",
                }

        # For now, return basic validation
        # Full precondition checking would require evaluating the AST
        return {
            "can_execute": True,
            "reason": "Action exists and entity found",
            "action": {
                "entity_type": action.entity_type,
                "action_name": action.action_name,
                "precondition_count": len(action.preconditions or []),
            },
        }
