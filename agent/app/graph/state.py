from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict):
    query: str

    intent: str
    tool: str
    reasoning: str

    region: str
    intervention: Dict[str, Any]

    missing_fields: List[str]

    context: str
    answer: str
    sources: List[str]
    memory: Dict[str, Any]
    followup_question: str