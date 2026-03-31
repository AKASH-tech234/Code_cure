"""
Agent graph nodes — API-safe, no CLI interaction.

Nodes:
1. planner_node — extracts intent, region, tool, missing fields
2. tool_node — dispatches to forecast/simulate/risk/rag tools
3. llm_node — synthesizes final answer from tool outputs

NO input(), NO print(), NO loops.
"""

import json
import logging
from ..llm.client import generate_answer
from ..tools.forecast_tool import forecast_tool
from ..tools.simulate_tool import simulate_tool
from ..tools.risk_tool import risk_tool
from ..tools.rag_tool import rag_tool

logger = logging.getLogger(__name__)


INTENT_REQUIRED_FIELDS = {
    "forecast": ["region_id"],
    "risk": ["region_id"],
    "simulate": ["region_id", "intervention"],
    "data_lookup": [],
    "general_info": [],
}


# ── NODE 1: PLANNER ──────────────────────────────────────────────────

def planner_node(state):
    """
    Extracts structured intent from user query + memory.
    Returns strict JSON with intent, tool, region, missing_fields.
    No CLI interaction — followup is returned as data, not asked interactively.
    """
    query = state["query"]
    memory = state.get("memory", {})

    prompt = f"""You are a precise AI planner for an epidemic intelligence system.

Known context from previous turns:
- region: {memory.get("region_id", "unknown")}
- last_intent: {memory.get("last_intent", "none")}
- previous_queries: {memory.get("previous_queries", [])}

User query: {query}

Extract structured data. You MUST return ONLY valid JSON, nothing else:

{{
  "intent": "forecast|simulate|risk|general_info",
  "tool": "forecast|simulate|risk|rag|none",
  "region": "ISO alpha-3 code or null",
  "intervention": {{
    "mobility_reduction": "float 0-1 or null",
    "vaccination_increase": "float 0-1 or null"
  }},
  "missing_fields": ["list of required but missing fields"],
  "reasoning": "one sentence explaining your decision",
  "followup_question": "natural question to ask if fields are missing, or empty string"
}}

Rules:
- If region is in memory but not in query, use memory region
- For forecast/risk intent, region is required
- For simulate intent, region AND intervention values are required
- For general_info, no fields required
- If a required field is missing, add it to missing_fields
- Region must be ISO alpha-3 (ITA, IND, USA, BRA, GBR, DEU, FRA, JPN, ZAF, AUS)
- Return ONLY the JSON, no markdown, no explanation"""

    response = generate_answer(prompt)

    try:
        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Merge memory-based region if planner didn't find one
        region = parsed.get("region") or memory.get("region_id") or ""

        # Build intervention dict
        intervention = parsed.get("intervention", {})
        if intervention:
            intervention = {
                "mobility_reduction": intervention.get("mobility_reduction"),
                "vaccination_increase": intervention.get("vaccination_increase"),
            }

        # Determine missing fields
        missing_fields = parsed.get("missing_fields", [])
        intent = parsed.get("intent", "general_info")
        tool = parsed.get("tool", "rag")

        # Auto-detect missing for forecast/risk
        if intent in ("forecast", "risk") and not region:
            if "region_id" not in missing_fields:
                missing_fields.append("region_id")

        # Auto-detect missing for simulate
        if intent == "simulate":
            if not region and "region_id" not in missing_fields:
                missing_fields.append("region_id")
            mobility = intervention.get("mobility_reduction")
            vaccination = intervention.get("vaccination_increase")
            if mobility is None or vaccination is None:
                if "intervention" not in missing_fields:
                    missing_fields.append("intervention")

        followup_question = parsed.get("followup_question", "")
        if missing_fields and not followup_question:
            followup_question = f"Could you please specify: {', '.join(missing_fields)}?"

        return {
            "intent": intent,
            "tool": tool,
            "region": region,
            "intervention": intervention,
            "missing_fields": missing_fields,
            "reasoning": parsed.get("reasoning", ""),
            "followup_question": followup_question,
            "verification_status": "pending",
            "verification_reason": "Planner completed; awaiting verifier gate.",
            "memory": {**memory, "region_id": region} if region else memory,
        }

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("[PLANNER] Failed to parse LLM output: %s", str(e))
        # Fallback: treat as general_info with rag
        return {
            "intent": "general_info",
            "tool": "rag",
            "region": memory.get("region_id", ""),
            "intervention": {},
            "missing_fields": [],
            "reasoning": "Could not parse planner output, falling back to RAG",
            "followup_question": "",
            "verification_status": "pending",
            "verification_reason": "Planner fallback path; awaiting verifier gate.",
            "memory": memory,
        }


def verifier_node(state):
    """
    Enforces pre-tool slot completeness checks.
    Blocks execution with follow-up details when required slots are missing.
    """
    intent = state.get("intent", "general_info")
    region = state.get("region", "")
    intervention = state.get("intervention") or {}

    required_fields = INTENT_REQUIRED_FIELDS.get(intent, [])
    missing_fields = set(state.get("missing_fields") or [])

    if "region_id" in required_fields and not region:
        missing_fields.add("region_id")

    if "intervention" in required_fields:
        if (
            intervention.get("mobility_reduction") is None
            or intervention.get("vaccination_increase") is None
        ):
            missing_fields.add("intervention")

    missing_list = sorted(missing_fields)

    followup_question = state.get("followup_question", "")
    if missing_list and not followup_question:
        followup_question = f"Could you please specify: {', '.join(missing_list)}?"

    if missing_list:
        return {
            "missing_fields": missing_list,
            "followup_question": followup_question,
            "verification_status": "missing_fields",
            "verification_reason": f"Missing required fields: {', '.join(missing_list)}",
        }

    return {
        "missing_fields": [],
        "verification_status": "ready",
        "verification_reason": "All required fields resolved; execution can proceed.",
    }


# ── NODE 2: TOOL EXECUTOR ────────────────────────────────────────────

def tool_node(state):
    """
    Dispatches to the appropriate tool based on planner output.
    Tools call external services — no hardcoded data.
    Returns normalized structured payloads and context string for synthesis.
    """
    tool = state.get("tool", "")
    region = state.get("region", "")
    intervention = state.get("intervention", {})
    query = state.get("query", "")

    context_parts = []
    sources = []
    tool_payloads = {}

    try:
        if tool == "forecast":
            result = forecast_tool(region=region)
            tool_payloads["forecast"] = result
            context_parts.append(f"FORECAST DATA:\n{json.dumps(result, indent=2)}")

        elif tool == "simulate":
            result = simulate_tool(region=region, intervention=intervention)
            tool_payloads["simulate"] = result
            context_parts.append(f"SIMULATION DATA:\n{json.dumps(result, indent=2)}")

        elif tool == "risk":
            result = risk_tool(region=region)
            tool_payloads["risk"] = result
            context_parts.append(f"RISK ASSESSMENT:\n{json.dumps(result, indent=2)}")

        elif tool == "rag":
            rag_result = rag_tool(query)
            normalized_rag = {
                "context": rag_result.get("context", ""),
                "sources": rag_result.get("sources", []),
            }
            tool_payloads["rag"] = normalized_rag
            context_parts.append(f"KNOWLEDGE BASE:\n{normalized_rag['context']}")
            sources = normalized_rag["sources"]

        elif tool == "none":
            pass

        else:
            logger.warning("[TOOL] Unknown tool: %s", tool)

    except Exception as e:
        logger.error("[TOOL] Error executing %s: %s", tool, str(e))
        context_parts.append(f"[Tool error: {str(e)}]")

    # For forecast/simulate/risk, also try to get RAG context
    if tool in ("forecast", "simulate", "risk") and query:
        try:
            rag_result = rag_tool(query, top_k=3)
            normalized_rag = {
                "context": rag_result.get("context", ""),
                "sources": rag_result.get("sources", []),
            }
            if normalized_rag["context"]:
                tool_payloads["rag"] = normalized_rag
                context_parts.append(f"\nRELEVANT GUIDELINES:\n{normalized_rag['context']}")
                sources.extend(normalized_rag["sources"])
        except Exception as e:
            logger.warning("[TOOL] RAG supplemental call failed: %s", str(e))

    return {
        "context": "\n\n".join(context_parts),
        "sources": list(set(sources)),
        "tool_payloads": tool_payloads,
    }


# ── NODE 3: LLM SYNTHESIZER ──────────────────────────────────────────

def llm_node(state):
    """
    Synthesizes final answer from tool outputs.
    Produces structured, scientifically grounded explanation.
    """
    payloads = state.get("tool_payloads") or {}
    serialized_payloads = json.dumps(payloads, indent=2) if payloads else "{}"

    prompt = f"""You are an epidemic intelligence analyst.

User query: {state["query"]}

Planner reasoning: {state.get("reasoning", "")}

Structured tool outputs (JSON):
{serialized_payloads}

Additional context:
{state.get("context", "No data available.")}

Instructions:
- Use ONLY the provided tool outputs and context to answer
- Structure your answer clearly with sections
- If forecast data is present, summarize trends
- If risk data is present, explain risk drivers
- If simulation data is present, compare baseline vs intervention
- If guidelines are present, cite specific recommendations
- Never fabricate statistics
- Be concise but thorough
- Focus on actionable insights"""

    answer = generate_answer(prompt)

    return {"answer": answer}