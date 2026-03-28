from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    # INPUT
    query: str                              # User's natural language query
    memory: Dict[str, Any]                  # Injected session memory from gateway

    # PLANNING (filled by planner_node)
    intent: str                             # forecast | simulate | risk | general_info
    tool: str                               # forecast | simulate | risk | rag | none
    reasoning: str                          # Why this intent/tool was chosen
    region: str                             # ISO alpha-3 or empty
    intervention: Dict[str, Any]            # {mobility_reduction, vaccination_increase}

    # MISSING FIELDS (for followup)
    missing_fields: List[str]               # Fields still needed (e.g. ["region_id"])
    followup_question: str                  # Natural question to ask user
    verification_status: str                # ready | missing_fields
    verification_reason: str                # Human-readable verification result

    # TOOL OUTPUT
    context: str                            # Combined tool output (stringified)
    sources: List[str]                      # RAG source attributions
    tool_payloads: Dict[str, Any]           # Structured tool JSON outputs by tool name

    # FINAL OUTPUT
    answer: str                             # LLM-synthesized response