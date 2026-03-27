"""
Build the LangGraph agent — API-safe, no CLI interaction.

Graph flow:
  planner → conditional:
    ├─ missing_fields? → END (followup returned to frontend)
    ├─ tool="none"? → llm → END
    └─ else → tool → llm → END
"""

from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import planner_node, tool_node, llm_node
from .edges import route_after_planner


def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("tool", tool_node)
    graph.add_node("llm", llm_node)

    # Entry point
    graph.set_entry_point("planner")

    # Conditional edges from planner
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "end": END,        # missing fields → return followup
            "tool": "tool",    # has tool → execute it
            "llm": "llm",     # no tool needed → direct to LLM
        }
    )

    # tool → llm → END
    graph.add_edge("tool", "llm")
    graph.add_edge("llm", END)

    return graph.compile()