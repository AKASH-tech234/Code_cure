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
            if not intervention.get("mobility_reduction") and not intervention.get("vaccination_increase"):
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
            "memory": memory,
        }


# ── NODE 2: TOOL EXECUTOR ────────────────────────────────────────────

def tool_node(state):
    """
    Dispatches to the appropriate tool based on planner output.
    Tools call external services — no hardcoded data.
    Returns context string for the synthesizer.
    """
    tool = state.get("tool", "")
    region = state.get("region", "")
    intervention = state.get("intervention", {})
    query = state.get("query", "")

    context_parts = []
    sources = []

    try:
        if tool == "forecast":
            result = forecast_tool(region=region)
            context_parts.append(f"FORECAST DATA:\n{json.dumps(result, indent=2)}")

        elif tool == "simulate":
            result = simulate_tool(region=region, intervention=intervention)
            context_parts.append(f"SIMULATION DATA:\n{json.dumps(result, indent=2)}")

        elif tool == "risk":
            result = risk_tool(region=region)
            context_parts.append(f"RISK ASSESSMENT:\n{json.dumps(result, indent=2)}")

        elif tool == "rag":
            rag_result = rag_tool(query)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_result.get('context', '')}")
            sources = rag_result.get("sources", [])

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
            if rag_result.get("context"):
                context_parts.append(f"\nRELEVANT GUIDELINES:\n{rag_result['context']}")
                sources.extend(rag_result.get("sources", []))
        except Exception as e:
            logger.warning("[TOOL] RAG supplemental call failed: %s", str(e))

    return {
        "context": "\n\n".join(context_parts),
        "sources": list(set(sources)),
    }


# ── NODE 3: LLM SYNTHESIZER ──────────────────────────────────────────

def llm_node(state):
    """
    Synthesizes final answer from tool outputs.
    Produces structured, scientifically grounded explanation.
    """
    prompt = f"""You are an epidemic intelligence analyst.

User query: {state["query"]}

Planner reasoning: {state.get("reasoning", "")}

Data and context:
{state.get("context", "No data available.")}

Instructions:
- Use ONLY the provided data to answer
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