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

    async def query_tools_node(self, state: AgentState) -> AgentState:
        """Execute query tools to gather information.

        This node uses tool calling with the LLM to execute
        the appropriate query tools based on the user's question.

        Supports multi-turn tool execution for complex queries.

        Args:
            state: Current agent state

        Returns:
            Updated state with query results
        """
        logger.info("Executing query tools node")

        # Prepare messages with system prompt
        messages_with_prompt = await self.query_prompt.ainvoke({"messages": state["messages"]})

        # Track current messages for multi-turn conversation
        current_messages = list(messages_with_prompt)

        # Multi-turn tool execution loop
        max_iterations = 10  # Prevent infinite loops
        for iteration in range(max_iterations):
            # Get response from LLM
            response = await self.query_llm_with_tools.ainvoke(current_messages)
            current_messages.append(response)

            # Check if there are tool calls
            if not (hasattr(response, "tool_calls") and response.tool_calls):
                # No more tool calls, exit loop
                break

            # Execute all tool calls in this round
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                # Find and execute the tool
                tool = next((t for t in self.query_tools if t.name == tool_name), None)
                if tool:
                    try:
                        logger.info(f"Executing query tool: {tool_name} with args: {tool_args}")
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

            # Add tool messages to conversation
            current_messages.extend(tool_messages)
            logger.info(f"Query iteration {iteration + 1}, executed {len(tool_messages)} tools")

        # Update state with all messages (except the system prompt)
        state["messages"].extend(current_messages[1:])

        state["current_step"] = "queried"

        return state

    async def action_tools_node(self, state: AgentState) -> AgentState:
        """Plan and execute action operations.

        This node uses both query and action tools to:
        1. Identify target entities using query tools
        2. Execute actions using action tools
        3. Return results with success/failure breakdown

        Args:
            state: Current agent state

        Returns:
            Updated state with action results
        """
        logger.info("Executing action tools node")

        # Combine query and action tools for full capability
        all_tools = self.query_tools + self.action_tools

        # Bind all tools to LLM
        llm_with_all_tools = self.llm.bind_tools(all_tools)

        # Prepare messages with system prompt
        messages_with_prompt = await self.action_prompt.ainvoke({"messages": state["messages"]})

        # Track current messages for multi-turn conversation
        current_messages = list(messages_with_prompt)

        # Multi-turn tool execution loop
        max_iterations = 10  # Prevent infinite loops
        for iteration in range(max_iterations):
            # Get response from LLM
            response = await llm_with_all_tools.ainvoke(current_messages)
            current_messages.append(response)

            # Check if there are tool calls
            if not (hasattr(response, "tool_calls") and response.tool_calls):
                # No more tool calls, exit loop
                break

            # Execute all tool calls in this round
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                # Find tool in either query or action tools
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

            # Add tool messages to conversation
            current_messages.extend(tool_messages)
            logger.info(f"Completed iteration {iteration + 1}, executed {len(tool_messages)} tools")

        # Update state with all messages
        state["messages"].extend(current_messages[1:])  # Skip the system prompt message

        state["current_step"] = "action_executed"

        return state

    async def answer_node(self, state: AgentState) -> AgentState:
        """Generate a direct answer without tools.

        This node handles general conversation and direct answers.

        Args:
            state: Current agent state

        Returns:
            Updated state with AI response
        """
        logger.info("Executing answer node")

        last_message = state["messages"][-1]

        if hasattr(last_message, "content"):
            user_input = last_message.content
        else:
            user_input = str(last_message)

        # Simple response for direct answer
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个知识图谱助手。简洁友好地回应用户。"),
            ("human", "{input}")
        ])

        chain = prompt | self.llm

        try:
            result = await chain.ainvoke({"input": user_input})
            ai_message = AIMessage(content=result.content)
        except Exception as e:
            logger.error(f"Error in answer_node: {e}")
            ai_message = AIMessage(content="抱歉，我现在无法处理您的请求。")

        state["messages"].append(ai_message)
        state["current_step"] = "answered"

        return state

    async def summary_node(self, state: AgentState) -> AgentState:
        """Summarize action execution results.

        This node creates a summary of batch action execution.
        The actual action execution happens in action_tools_node,
        this node just ensures we have a final message.

        Args:
            state: Current agent state

        Returns:
            Updated state with summary
        """
        logger.info("Executing summary node")

        # Check if we have action results in messages
        # If not, add a completion message
        last_message = state["messages"][-1]

        # If the last message is already an AI response, we're done
        if isinstance(last_message, AIMessage):
            state["current_step"] = "completed"
            return state

        # Add a completion message
        ai_message = AIMessage(content="操作执行完成。")
        state["messages"].append(ai_message)
        state["current_step"] = "completed"

        return state


def route_decision(state: AgentState) -> Literal["query_tools", "action_tools", "answer"]:
    """Decide which node to route to based on user intent.

    Args:
        state: Current agent state

    Returns:
        Name of the next node to execute
    """
    intent = state.get("user_intent", UserIntent.QUERY)

    if intent == UserIntent.QUERY:
        return "query_tools"
    elif intent == UserIntent.ACTION:
        return "action_tools"
    else:
        return "answer"
