"""LangGraph construction for the enhanced agent."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from app.services.agent.state import AgentState
from app.services.agent.nodes import AgentNodes, should_continue


def create_agent_graph(
    llm: ChatOpenAI,
    query_tools: list,
    action_tools: list | None = None,
    with_memory: bool = True,
) -> StateGraph:
    """Create the LangGraph state graph for the enhanced agent.

    The graph structure:
        Start -> Agent -> Should Continue? -> Tools -> Agent
                         |
                         v
                       Answer -> End

    Args:
        llm: The LLM instance
        query_tools: List of query tools
        action_tools: List of action tools (optional)
        with_memory: Whether to enable memory checkpointing

    Returns:
        Compiled StateGraph ready for invocation
    """
    # Create agent nodes
    nodes = AgentNodes(llm=llm, query_tools=query_tools, action_tools=action_tools)

    # Create the workflow
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", nodes.agent_node)
    workflow.add_node("tools", nodes.execute_tools_node)
    workflow.add_node("answer", nodes.answer_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "answer",
        }
    )

    # Add edges
    workflow.add_edge("tools", "agent")
    workflow.add_edge("answer", END)

    # Compile with optional memory
    checkpointer = MemorySaver() if with_memory else None
    graph = workflow.compile(checkpointer=checkpointer)

    return graph


def visualize_graph(graph: StateGraph, output_path: str | None = None) -> str:
    """Generate a visual representation of the graph.

    Args:
        graph: The compiled StateGraph
        output_path: Optional path to save the visualization

    Returns:
        Mermaid diagram source
    """
    try:
        from langchain_core.runnables.graph import MermaidDrawStream

        if output_path:
            with open(output_path, "w") as f:
                f.write(graph.get_graph().draw_mermaid())

        return graph.get_graph().draw_mermaid()
    except Exception as e:
        return f"Could not generate visualization: {e}"
