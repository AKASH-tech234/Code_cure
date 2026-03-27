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


def _day_labels(values: list) -> list[str]:
    return [f"Day {index + 1}" for index in range(len(values))]


def _forecast_chart(predicted_cases: list[int]) -> dict:
    return {
        "chart_type": "line",
        "x_axis_label": "Day",
        "y_axis_label": "Predicted Cases",
        "labels": _day_labels(predicted_cases),
        "series": [
            {
                "name": "predicted_cases",
                "values": predicted_cases,
            }
        ],
    }


def _simulate_chart(baseline_cases: list[int], simulated_cases: list[int], delta_cases: int | None) -> dict:
    chart_len = min(len(baseline_cases), len(simulated_cases))
    baseline = baseline_cases[:chart_len]
    simulated = simulated_cases[:chart_len]

    return {
        "chart_type": "line",
        "x_axis_label": "Day",
        "y_axis_label": "Cases",
        "labels": _day_labels(baseline),
        "series": [
            {
                "name": "baseline_cases",
                "values": baseline,
            },
            {
                "name": "simulated_cases",
                "values": simulated,
            },
        ],
        "summary": {
            "delta_cases": delta_cases,
        },
    }


def _primary_tool(tool: str, tool_payloads: dict) -> str:
    if tool and tool != "none":
        return tool

    for candidate in ("simulate", "forecast", "risk", "rag"):
        if candidate in tool_payloads:
            return candidate

    return ""


def _extract_structured_data(tool: str, tool_payloads: dict) -> dict | None:
    payloads = tool_payloads or {}
    selected_tool = _primary_tool(tool, payloads)

    if selected_tool == "forecast":
        data = payloads.get("forecast")
        if not isinstance(data, dict) or not data:
            return None
        predicted_cases = data.get("predicted_cases") or []
        if not isinstance(predicted_cases, list):
            predicted_cases = []
        return {
            "kind": "forecast",
            "region_id": data.get("region_id"),
            "risk_score": data.get("risk_score"),
            "risk_level": data.get("risk_level"),
            "growth_rate": data.get("growth_rate"),
            "predicted_cases": predicted_cases,
            "horizon_days": data.get("horizon_days"),
            "as_of_date": data.get("as_of_date"),
            "chart": _forecast_chart(predicted_cases),
        }

    if selected_tool == "simulate":
        data = payloads.get("simulate")
        if not isinstance(data, dict) or not data:
            return None
        baseline_cases = data.get("baseline_cases") or []
        simulated_cases = data.get("simulated_cases") or []
        if not isinstance(baseline_cases, list):
            baseline_cases = []
        if not isinstance(simulated_cases, list):
            simulated_cases = []
        return {
            "kind": "simulate",
            "region_id": data.get("region_id"),
            "baseline_cases": baseline_cases,
            "simulated_cases": simulated_cases,
            "delta_cases": data.get("delta_cases"),
            "impact_summary": data.get("impact_summary"),
            "chart": _simulate_chart(
                baseline_cases=baseline_cases,
                simulated_cases=simulated_cases,
                delta_cases=data.get("delta_cases"),
            ),
        }

    if selected_tool == "risk":
        data = payloads.get("risk")
        if not isinstance(data, dict) or not data:
            return None
        return {
            "kind": "risk",
            "region_id": data.get("region_id"),
            "risk_score": data.get("risk_score"),
            "risk_level": data.get("risk_level"),
            "drivers": data.get("drivers") or [],
        }

    if selected_tool == "rag":
        data = payloads.get("rag")
        if not isinstance(data, dict):
            return None
        context = data.get("context") or ""
        sources = data.get("sources") or []
        return {
            "kind": "rag",
            "source_count": len(sources),
            "has_context": bool(context.strip()),
        }

    return None


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
        "structured_data": dict or None,
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
            "tool_payloads": {},
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

        structured_data = _extract_structured_data(
            result.get("tool") or "",
            result.get("tool_payloads") or {},
        )

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
            "structured_data": structured_data if not followup else None,
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
            "structured_data": None,
            "followup": None,
            "memory_updates": {"query": query},
            "error": str(e),
        }
