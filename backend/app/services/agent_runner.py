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
from typing import Any

logger = logging.getLogger(__name__)

# Add repository root to path so we can import the agent package explicitly.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.app.graph.state import AgentState


INTENT_REQUIRED_FIELDS: dict[str, list[str]] = {
    "forecast": ["region_id"],
    "risk": ["region_id"],
    "simulate": ["region_id", "intervention"],
    "data_lookup": [],
    "general_info": [],
}


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


def _has_intervention(intervention: dict[str, Any] | None) -> bool:
    if not isinstance(intervention, dict):
        return False

    return (
        intervention.get("mobility_reduction") is not None
        and intervention.get("vaccination_increase") is not None
    )


def _build_slot_status(intent: str, region: str, intervention: dict[str, Any], missing_fields: list[str]) -> dict:
    required_fields = INTENT_REQUIRED_FIELDS.get(intent, [])

    resolved_fields: list[str] = []
    if region:
        resolved_fields.append("region_id")
    if _has_intervention(intervention):
        resolved_fields.append("intervention")

    missing_set = set(missing_fields or [])

    # Guarantee response consistency even if planner underreports required fields.
    for required in required_fields:
        if required not in resolved_fields:
            missing_set.add(required)

    missing = sorted(missing_set)

    return {
        "required_fields": required_fields,
        "resolved_fields": resolved_fields,
        "missing_fields": missing,
        "is_complete": len(missing) == 0,
    }


def _build_verification(slot_status: dict, error: str | None = None) -> dict:
    if error:
        return {
            "status": "error",
            "can_execute": False,
            "reason": error,
        }

    if not slot_status.get("is_complete", False):
        return {
            "status": "missing_fields",
            "can_execute": False,
            "reason": f"Missing required fields: {', '.join(slot_status.get('missing_fields', []))}",
        }

    return {
        "status": "ready",
        "can_execute": True,
        "reason": None,
    }


def _build_execution_steps(tool: str, missing_fields: list[str], error: str | None = None) -> list[dict]:
    if error:
        return [
            {"step": "planner", "status": "failed", "detail": "Graph execution failed before completion."},
            {"step": "tool", "status": "skipped", "detail": "Execution aborted due to error."},
            {"step": "llm", "status": "skipped", "detail": "Execution aborted due to error."},
        ]

    if missing_fields:
        return [
            {"step": "planner", "status": "completed", "detail": "Intent and missing fields identified."},
            {"step": "tool", "status": "blocked", "detail": "Tool execution blocked until missing fields are provided."},
            {"step": "llm", "status": "skipped", "detail": "Final synthesis skipped until tool execution is possible."},
        ]

    if tool == "none":
        return [
            {"step": "planner", "status": "completed", "detail": "Query can be answered without tool execution."},
            {"step": "tool", "status": "skipped", "detail": "No tool selected by planner."},
            {"step": "llm", "status": "completed", "detail": "Answer synthesized directly."},
        ]

    return [
        {"step": "planner", "status": "completed", "detail": "Intent and slots resolved."},
        {"step": "tool", "status": "completed", "detail": f"Executed tool '{tool}'."},
        {"step": "llm", "status": "completed", "detail": "Answer synthesized from tool outputs."},
    ]


def run_agent(query: str, memory: dict, context: dict[str, Any] | None = None) -> dict:
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
        initial_state: AgentState = {
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
            "verification_status": "pending",
            "verification_reason": "",
        }

        # Override region from explicit context if provided
        if context and context.get("region_id"):
            initial_state["region"] = context["region_id"]
        if context and context.get("intervention"):
            initial_state["intervention"] = context["intervention"]

        # Run graph
        result = graph.invoke(initial_state)

        # Check for followup (missing fields)
        missing_fields = result.get("missing_fields") or []
        intent = result.get("intent") or "general_info"
        region = result.get("region") or ""
        intervention = result.get("intervention") or {}
        selected_tool = result.get("tool") or ""

        followup = None
        if missing_fields:
            followup = {
                "question": result.get("followup_question", "Could you provide more details?"),
                "missing_fields": missing_fields
            }

        structured_data = _extract_structured_data(
            selected_tool,
            result.get("tool_payloads") or {},
        )

        slot_status = _build_slot_status(
            intent=intent,
            region=region,
            intervention=intervention,
            missing_fields=missing_fields,
        )
        verification = _build_verification(slot_status=slot_status)
        if result.get("verification_status") == "missing_fields":
            verification = {
                "status": "missing_fields",
                "can_execute": False,
                "reason": result.get("verification_reason") or verification.get("reason"),
            }
        elif result.get("verification_status") == "ready":
            verification = {
                "status": "ready",
                "can_execute": True,
                "reason": result.get("verification_reason"),
            }
        execution_steps = _build_execution_steps(
            tool=selected_tool,
            missing_fields=missing_fields,
        )
        fallback_used = bool(
            (result.get("reasoning") or "").lower().startswith("could not parse planner output")
            or "[Tool error:" in (result.get("context") or "")
        )

        # Build memory updates
        memory_updates = {
            "query": query,
            "last_intent": intent,
        }
        if region:
            memory_updates["region_id"] = region
            memory_updates["resolved_fields"] = ["region_id"]
        if intervention:
            memory_updates["intervention"] = intervention

        return {
            "answer": result.get("answer") if not followup else None,
            "intent": intent,
            "tool": selected_tool,
            "reasoning": result.get("reasoning"),
            "sources": result.get("sources") or [],
            "structured_data": structured_data if not followup else None,
            "followup": followup,
            "slot_status": slot_status,
            "verification": verification,
            "execution_steps": execution_steps,
            "fallback_used": fallback_used,
            "memory_updates": memory_updates,
        }

    except Exception as e:
        logger.exception("[AGENT_RUNNER] Error running agent")
        error_message = str(e)

        slot_status = _build_slot_status(
            intent="general_info",
            region=memory.get("region_id") or "",
            intervention=memory.get("intervention") or {},
            missing_fields=[],
        )

        return {
            "answer": None,
            "intent": None,
            "tool": None,
            "reasoning": None,
            "sources": [],
            "structured_data": None,
            "followup": None,
            "slot_status": slot_status,
            "verification": _build_verification(slot_status=slot_status, error=error_message),
            "execution_steps": _build_execution_steps(tool="", missing_fields=[], error=error_message),
            "fallback_used": False,
            "memory_updates": {"query": query},
            "error": error_message,
        }
