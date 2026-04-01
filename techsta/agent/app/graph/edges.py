"""
Graph routing logic — deterministic, API-safe.
"""


def route_after_planner(state):
    """
    After planner:
    - If missing_fields → go to END (return followup via response)
    - If tool is "none" → go to llm directly
    - Otherwise → go to tool_node
    """
    if state.get("missing_fields"):
        return "end"

    if state.get("tool") == "none":
        return "llm"

    return "tool"
