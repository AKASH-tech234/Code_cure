import logging
from app.tools.rag_tool import rag_tool
from app.llm.client import generate_answer
from app.tools.forecast_tool import forecast_tool
from app.tools.simulate_tool import simulate_tool
logger = logging.getLogger(__name__)
import json
import json
from app.llm.client import generate_answer


def planner_node(state):
    query = state["query"]
    memory = state.get("memory", {})

    prompt = f"""
You are an AI planner.

Existing known information:
{memory}

Extract structured data from query.

Return JSON:

{{
  "intent": "...",
  "tool": "...",
  "region": "... or null",
  "intervention": {{
    "mobility_reduction": float or null,
    "vaccination_increase": float or null
  }},
  "missing_fields": [],
  "reasoning": "...",
  "followup_question": "if missing fields, ask a natural question"
}}

Rules:
- Merge previous known info with new query
- If something missing → add to missing_fields
- Also generate a natural followup_question

Query:
{query}
"""

    response = generate_answer(prompt)

    try:
        parsed = json.loads(response)

        # 🔥 merge memory
        new_memory = {**memory}

        if parsed.get("region"):
            new_memory["region"] = parsed["region"]

        if parsed.get("intervention"):
            new_memory.update(parsed["intervention"])

        return {
            "intent": parsed["intent"],
            "tool": parsed["tool"],
            "region": new_memory.get("region"),
            "intervention": {
                "mobility_reduction": new_memory.get("mobility_reduction"),
                "vaccination_increase": new_memory.get("vaccination_increase"),
            },
            "missing_fields": parsed.get("missing_fields", []),
            "reasoning": parsed.get("reasoning", ""),
            "followup_question": parsed.get("followup_question", ""),
            "memory": new_memory
        }

    except:
        return {"missing_fields": [], "memory": memory}
    
    
from app.tools.forecast_tool import forecast_tool
from app.tools.simulate_tool import simulate_tool
from app.tools.rag_tool import rag_tool


def followup_node(state):
    question = state.get("followup_question")

    if not state.get("missing_fields"):
        return {}

    print("\n🤖:", question)

    user_input = input("👤: ")

    # 🔥 update query
    return {
        "query": user_input
    }

def tool_node(state):
    tool = state.get("tool")

    if tool == "forecast_tool":
        return {
            "context": forecast_tool(
                region=state["region"]
            )
        }

    elif tool == "simulate_tool":
        return {
            "context": simulate_tool(
                region=state["region"],
                intervention=state["intervention"]
            )
        }

    elif tool == "rag_tool":
        return rag_tool(state["query"])

    return {}

# def human_input_node(state):
#     missing = state.get("missing_fields", [])

#     if not missing:
#         return {}

#     print("\n⚠️ Missing required fields:", missing)

#     updated = {}

#     for field in missing:
#         value = input(f"Please provide {field}: ")
#         updated[field] = value

#     return updated
def rag_node(state):
    if state.get("tool") != "rag_tool":
        return {"context": "", "sources": []}

    query = state["query"]

    res = rag_tool(query)

    return {
        "context": res["context"],
        "sources": res["sources"]
    }
def llm_node(state):
    prompt = f"""
You are an epidemiology expert.

Planner reasoning:
{state.get("reasoning")}

User query:
{state["query"]}

Data:
{state.get("context")}

Provide a clear explanation.
"""

    return {"answer": generate_answer(prompt)}