from .forecast_tool import forecast_tool
from .simulate_tool import simulate_tool
from .risk_tool import risk_tool
from .rag_tool import rag_tool

TOOL_REGISTRY = {
    "forecast": forecast_tool,
    "simulate": simulate_tool,
    "risk": risk_tool,
    "rag": rag_tool,
}
