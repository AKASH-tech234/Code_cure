"""
Agent runner: bridges the gateway with the LangGraph agent.

Responsibilities:
1. Inject session memory into AgentState
2. Call graph.invoke()
3. Extract structured response
4. Return memory updates for persistence
"""

import sys
import os
import logging

logger = logging.getLogger(__name__)

# Add repository root to path so we can import the agent package explicitly.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def run_agent(query: str, memory: dict, context: dict = None) -> dict:
    """
    Run the LangGraph agent with injected memory.

    Returns:
    {
        "answer": str or None,
        "intent": str or None,
        "tool": str or None,
        "reasoning": str or None,
        "sources": list[str],
        "followup": {"question": str, "missing_fields": list} or None,
        "memory_updates": dict  # fields to persist in session
    }
    """
    try:
        from agent.app.graph.build_graph import build_graph

        graph = build_graph()

        # Build initial state from memory + query
        initial_state = {
            "query": query,
            "intent": "",
            "tool": "",
            "reasoning": "",
            "region": memory.get("region_id") or "",
            "intervention": memory.get("intervention") or {},
            "missing_fields": [],
            "context": "",
            "answer": "",
            "sources": [],
            "memory": memory,
            "followup_question": "",
        }

        # Override region from explicit context if provided
        if context and context.get("region_id"):
            initial_state["region"] = context["region_id"]
        if context and context.get("intervention"):
            initial_state["intervention"] = context["intervention"]

        # Run graph
        result = graph.invoke(initial_state)

        # Check for followup (missing fields)
        followup = None
        if result.get("missing_fields"):
            followup = {
                "question": result.get("followup_question", "Could you provide more details?"),
                "missing_fields": result["missing_fields"]
            }

        # Build memory updates
        memory_updates = {
            "query": query,
            "last_intent": result.get("intent"),
        }
        if result.get("region"):
            memory_updates["region_id"] = result["region"]
            memory_updates["resolved_fields"] = ["region_id"]
        if result.get("intervention"):
            memory_updates["intervention"] = result["intervention"]

        return {
            "answer": result.get("answer") if not followup else None,
            "intent": result.get("intent"),
            "tool": result.get("tool"),
            "reasoning": result.get("reasoning"),
            "sources": result.get("sources") or [],
            "followup": followup,
            "memory_updates": memory_updates,
        }

    except Exception as e:
        logger.exception("[AGENT_RUNNER] Error running agent")
        return {
            "answer": None,
            "intent": None,
            "tool": None,
            "reasoning": None,
            "sources": [],
            "followup": None,
            "memory_updates": {"query": query},
            "error": str(e),
        }
