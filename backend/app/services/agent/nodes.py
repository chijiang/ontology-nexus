"""LangGraph node implementations for the enhanced agent."""

import logging
from typing import Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from app.services.agent.state import AgentState, UserIntent
from app.services.agent.prompts import (
    QUERY_SYSTEM_PROMPT,
    ACTION_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)


class AgentNodes:
    """Collection of LangGraph node functions.

    Each node is an async function that takes the current state
    and returns an updated state.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        query_tools: list[BaseTool],
        action_tools: list | None = None,
    ):
        """Initialize agent nodes.

        Args:
            llm: The LLM instance for decision making and responses
            query_tools: List of query tools for knowledge graph queries
            action_tools: List of action tools for executing operations
        """
        self.llm = llm
        self.query_tools = query_tools
        self.action_tools = action_tools or []

        # Bind tools to LLM for query operations
        self.query_llm_with_tools = llm.bind_tools(query_tools)

        # Create prompts
        self.query_prompt = ChatPromptTemplate.from_messages([
            ("system", QUERY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])

        self.action_prompt = ChatPromptTemplate.from_messages([
            ("system", ACTION_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])

        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_CLASSIFICATION_PROMPT),
            ("human", "{input}"),
        ])

    async def router_node(self, state: AgentState) -> AgentState:
        """Determine the user's intent and route to appropriate handler.

        This node classifies the user's message into:
        - QUERY: Information seeking, needs query tools
        - ACTION: Wants to perform operations, needs action tools
        - DIRECT_ANSWER: General conversation, no tools needed

        Args:
            state: Current agent state

        Returns:
            Updated state with classified intent
        """
        last_message = state["messages"][-1]

        # Get user input
        if hasattr(last_message, "content"):
            user_input = last_message.content
        else:
            user_input = str(last_message)

        logger.info(f"Router processing: {user_input[:100]}...")

        # Simple keyword-based intent classification
        # More sophisticated LLM-based classification can be added
        user_input_lower = user_input.lower()

        # Action keywords (Chinese and English)
        action_keywords = [
            "执行", "运行", "操作", "处理", "付款", "支付", "提交", "批准", "删除", "更新", "修改",
            "execute", "run", "perform", "pay", "submit", "approve", "delete", "update", "modify"
        ]

        # Query keywords
        query_keywords = [
            "查找", "搜索", "显示", "展示", "列出", "有多少", "什么是", "哪个", "查询",
            "find", "search", "show", "list", "how many", "what is", "which", "query"
        ]

        # Check for action intent
        if any(keyword in user_input_lower for keyword in action_keywords):
            intent = UserIntent.ACTION
        # Check for query intent
        elif any(keyword in user_input_lower for keyword in query_keywords):
            intent = UserIntent.QUERY
        # Default to query
        else:
            intent = UserIntent.QUERY

        logger.info(f"Classified intent as: {intent}")

        state["user_intent"] = intent
        state["current_step"] = "routed"

        return state

    async def agent_node(self, state: AgentState) -> AgentState:
        """Unified agent node that can query or act.

        This node uses all available tools and the LLM to process the request.
        It supports multi-turn tool execution by being part of a loop.

        Args:
            state: Current agent state

        Returns:
            Updated state with LLM response or tool results
        """
        logger.info("--- agent_node started ---")
        
        # Combine all tools
        all_tools = self.query_tools + self.action_tools
        llm_with_tools = self.llm.bind_tools(all_tools)

        # Prepare messages
        # We use all messages in state to maintain context
        messages = state["messages"]
        
        # Add system prompt if it's the first turn
        if len(messages) == 1 and isinstance(messages[0], (str, dict)):
            # This shouldn't happen with standard LangGraph but good to be safe
            prompt_result = await self.action_prompt.ainvoke({"messages": messages})
            messages = prompt_result.to_messages()
        elif not any(isinstance(m, (AIMessage, ToolMessage)) for m in messages):
            # First turn, inject system prompt
            prompt_result = await self.action_prompt.ainvoke({"messages": messages})
            messages = prompt_result.to_messages()

        # Get response from LLM
        response = await llm_with_tools.ainvoke(messages)
        
        logger.info(f"LLM response: {str(response.content)[:100]}...")
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Tool calls: {[tc.get('name') for tc in response.tool_calls]}")

        # Update state
        return {"messages": [response]}

    async def execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute tool calls from the last AIMessage.

        Args:
            state: Current agent state

        Returns:
            Updated state with ToolMessages
        """
        logger.info("--- execute_tools_node started ---")
        last_message = state["messages"][-1]
        
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return state

        all_tools = self.query_tools + self.action_tools
        tool_messages = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            tool = next((t for t in all_tools if t.name == tool_name), None)
            if tool:
                try:
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    result = await tool.ainvoke(tool_args)
                    tool_messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    tool_messages.append(ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_id,
                        name=tool_name
                    ))
            else:
                logger.warning(f"Tool not found: {tool_name}")
                tool_messages.append(ToolMessage(
                    content=f"Error: Tool '{tool_name}' not found",
                    tool_call_id=tool_id,
                    name=tool_name
                ))

        return {"messages": tool_messages}

    async def answer_node(self, state: AgentState) -> AgentState:
        """Final answer node (basically a pass-through now)."""
        state["current_step"] = "completed"
        return state


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Decide whether to continue tool execution or end.

    Args:
        state: Current agent state

    Returns:
        "tools" if more tool calls are present, "end" otherwise
    """
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    return "end"
