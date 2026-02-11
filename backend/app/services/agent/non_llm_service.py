import json
import logging
import re
import os
from typing import Any, AsyncIterator, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.state import StreamEvent
from app.rule_engine.action_executor import ActionExecutor
from app.services.agent_tools.query_tools import create_query_tools
from app.services.agent_tools.action_tools import create_action_tools

logger = logging.getLogger(__name__)


class NonLLMService:
    def __init__(self):
        self.templates = []
        try:
            current_dir = os.path.dirname(__file__)
            template_path = os.path.join(
                current_dir, "../../data/non_llm_templates.json"
            )
            with open(template_path, "r") as f:
                self.templates = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Non-LLM templates: {e}")

    async def match_and_execute(
        self,
        query: str,
        db: AsyncSession,
        action_executor: Optional[ActionExecutor] = None,
        action_registry: Optional[Any] = None,
    ) -> AsyncIterator[StreamEvent]:

        matched_template = None
        extracted_params = {}

        for template in self.templates:
            for pattern in template["patterns"]:
                # Convert template pattern to regex
                # Escape all regex specials, then unescape the {} placeholders we want to keep?
                # Safer: Split by {param} and reassemble.
                # Or use the previous logic which was okay: replace \{name\} with (?P<name>.+?)

                safe_pattern = re.escape(pattern)
                # re.escape escapes {, }, etc.
                # We want to replace \{param_name\} with (?P<param_name>.+?)

                regex_pattern = re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+?)", safe_pattern)
                regex_pattern = f"^{regex_pattern}$"

                match = re.match(regex_pattern, query.strip())
                if match:
                    matched_template = template
                    extracted_params = match.groupdict()
                    break
            if matched_template:
                break

        if not matched_template:
            return

        yield {
            "type": "thinking",
            "content": f"Matched pattern: {matched_template['id']}",
        }

        # Initialize Event Emitter for Graph Data
        from app.rule_engine.event_emitter import GraphEventEmitter
        from app.rule_engine.models import GraphViewEvent

        event_emitter = GraphEventEmitter()
        graph_events = []

        def on_graph_event(event: Any):
            if isinstance(event, GraphViewEvent):
                graph_events.append(event)

        event_emitter.subscribe(on_graph_event)

        try:
            # Context manager wrapper for existing session
            class SessionWrapper:
                def __init__(self, session):
                    self.session = session

                async def __aenter__(self):
                    return self.session

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            def get_session_context():
                return SessionWrapper(db)

            # Initialize tools with event_emitter
            query_tools = create_query_tools(get_session_context, event_emitter)
            action_tools = []
            if action_executor and action_registry:
                action_tools = create_action_tools(
                    get_session_context, action_executor, action_registry
                )

            all_tools = {t.name: t for t in query_tools + action_tools}

            tool_name = matched_template.get("tool")
            if not tool_name:
                yield {
                    "type": "content",
                    "content": "Configuration error: No tool defined for this template.",
                }
                return

            if tool_name not in all_tools:
                yield {
                    "type": "content",
                    "content": f"Configuration error: Tool '{tool_name}' not found.",
                }
                return

            tool = all_tools[tool_name]

            # Prepare arguments
            def replace_placeholders(val):
                if isinstance(val, str):
                    for param_key, param_val in extracted_params.items():
                        val = val.replace(f"{{{param_key}}}", param_val)
                    return val
                elif isinstance(val, dict):
                    return {k: replace_placeholders(v) for k, v in val.items()}
                elif isinstance(val, list):
                    return [replace_placeholders(v) for v in val]
                return val

            tool_args = replace_placeholders(matched_template.get("args", {}))

            yield {
                "type": "thinking",
                "content": f"\nExecuting tool: `{tool_name}` with args: {tool_args}...",
            }

            # Execute tool
            try:
                result_str = str(await tool.ainvoke(tool_args))

                # Yield any captured graph events first
                for graph_event in graph_events:
                    yield {
                        "type": "graph_data",
                        "nodes": graph_event.nodes,
                        "edges": graph_event.edges,
                    }

                yield {"type": "content", "content": result_str}
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                yield {"type": "content", "content": f"Error executing tool: {str(e)}"}

        except Exception as e:
            logger.error(f"Error executing Non-LLM query: {e}", exc_info=True)
            yield {"type": "content", "content": f"处理请求时发生错误: {str(e)}"}
        finally:
            event_emitter.unsubscribe(on_graph_event)
