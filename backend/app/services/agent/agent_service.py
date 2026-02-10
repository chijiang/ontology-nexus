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

        # Initialize Event Emitter for Graph Data
        from app.rule_engine.event_emitter import GraphEventEmitter

        self.event_emitter = GraphEventEmitter()

        # Initialize graph (lazy loading)
        self._graph = None

    def _get_session(self):
        """Get a database session context manager for query tools.

        Returns an async context manager that yields a database session.
        """
        from app.core.database import async_session

        class SessionContextManager:
            def __init__(self):
                self._session = None

            async def __aenter__(self):
                self._session = async_session()
                return await self._session.__aenter__()

            async def __aexit__(self, *args):
                if self._session:
                    await self._session.__aexit__(*args)

        return SessionContextManager()

    def _get_graph(self):
        """Get or create the LangGraph."""
        if self._graph is None:
            # Create query tools registry
            query_registry = QueryToolRegistry(self._get_session, self.event_emitter)
            query_tools = query_registry.tools

            # Create action tools if action_executor and action_registry are available
            action_tools = []
            if self.action_executor and self.action_registry:
                action_registry = ActionToolRegistry(
                    self._get_session, self.action_executor, self.action_registry
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

    async def astream_chat(
        self, query: str, history: list[dict] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Stream chat responses with real-time updates.

        This method yields events as the agent processes the request,
        including thinking, tool calls, and final results.

        Args:
            query: User's query or request
            history: Optional list of previous messages [{"role": "user", "content": "..."}]

        Yields:
            StreamEvent objects with type and content
        """
        from langchain_core.messages import HumanMessage, AIMessage
        from app.rule_engine.models import GraphViewEvent
        import asyncio

        logger.info(f"=== Agent astream_chat started ===")
        logger.info(f"User query: {query}")
        if history:
            logger.info(f"History rounds: {len(history) // 2}")

        # Queue for graph events
        graph_events_queue = asyncio.Queue()

        def on_graph_event(event: Any):
            if isinstance(event, GraphViewEvent):
                try:
                    graph_events_queue.put_nowait(event)
                except Exception as e:
                    logger.error(f"Error putting event in queue: {e}")

        # Subscribe to graph events
        self.event_emitter.subscribe(on_graph_event)

        # Initial thinking event
        yield {
            "type": "thinking",
            "content": "正在分析您的请求...",
        }

        try:
            # Get the graph
            graph = self._get_graph()
            action_count = (
                len(self.action_registry._actions) if self.action_registry else 0
            )
            logger.info(f"Graph created, actions in registry: {action_count}")

            # Prepare initial messages with history
            messages = []
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

            # Add current query
            messages.append(HumanMessage(content=query))

            # Create initial state
            initial_state: AgentState = {
                "messages": messages,
            }

            # Stream the graph execution with granular events
            async for event in graph.astream_events(initial_state, version="v2"):

                # Check for graph events from queue (e.g. visualization data from tools)
                while not graph_events_queue.empty():
                    graph_event = graph_events_queue.get_nowait()
                    yield {
                        "type": "graph_data",
                        "nodes": graph_event.nodes,
                        "edges": graph_event.edges,
                    }

                kind = event["event"]

                # 1. Token-level streaming from LLM
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {
                            "type": "thinking",
                            "content": content,
                        }

                # 2. End of a model turn - check if we should emit content
                elif kind == "on_chat_model_end":
                    ai_msg = event["data"]["output"]
                    # If this is a final answer (no tool calls), emit as content
                    if hasattr(ai_msg, "tool_calls") and not ai_msg.tool_calls:
                        content = ai_msg.content or ""
                        # Skip if it's just our placeholder
                        if "[注意：Action 执行功能将在 Phase 2 中实现]" in content:
                            content = content.replace(
                                "\n\n[注意：Action 执行功能将在 Phase 2 中实现]", ""
                            )

                        if content:
                            yield {
                                "type": "content",
                                "content": content,
                            }

                    # Log tool calls for debugging
                    if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                        logger.info(f"Tool calls detected: {len(ai_msg.tool_calls)}")
                        for tc in ai_msg.tool_calls:
                            logger.info(f"  - Tool: {tc.get('name')}")

                # 3. Tool execution start events
                elif kind == "on_tool_start":
                    yield {
                        "type": "thinking",
                        "content": f"\n\n> **正在调用工具**: `{event['name']}`...\n",
                    }

                # 4. Node markers (optional, for logging)
                elif kind == "on_chain_start" and event.get("metadata", {}).get(
                    "langgraph_node"
                ):
                    node_name = event["metadata"]["langgraph_node"]
                    logger.info(f"=== Entering Node: {node_name} ===")

                    # For some specific nodes, we can add a separator
                    if node_name == "tools":
                        yield {
                            "type": "thinking",
                            "content": "\n\n",
                        }

        except Exception as e:
            logger.error(f"Error in astream_chat: {e}", exc_info=True)
            yield {
                "type": "content",
                "content": f"\n\n抱歉，处理请求时发生错误: {str(e)}",
            }
        finally:
            try:
                self.event_emitter.unsubscribe(on_graph_event)
            except Exception:
                pass

        # Final done event
        yield {"type": "done"}

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
