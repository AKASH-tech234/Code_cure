from langgraph.graph import StateGraph
from app.graph.state import AgentState
from app.graph.nodes import (
    planner_node,
    tool_node,
    followup_node,
    llm_node
)

def route_after_planner(state):
    if state.get("missing_fields"):
        return "followup"

    if state.get("tool") == "none":
        return "llm"

    return "tool"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("followup", followup_node)
    graph.add_node("tool", tool_node)
    graph.add_node("llm", llm_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", route_after_planner)

    graph.add_edge("followup", "planner")   # 🔁 loop back

    graph.add_edge("tool", "llm")

    graph.set_finish_point("llm")

    return graph.compile()