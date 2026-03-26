# 🧠 Epidemic Intelligence System — Track C Implementation Plan

> **CODECURE AI Hackathon | Corrected Architecture + Micro-Step Execution Guide**
> **5-Day Build Plan | Small Team Optimized**

### ✅ Corrected Architecture (Component-Precise)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                                │
│   MapView │ ForecastChart │ ScenarioSliders │ ChatUI │ RiskBadge       │
└─────────────────────────┬──────────────────────────────────────────────┘
                          │ HTTP / WebSocket
┌─────────────────────────▼──────────────────────────────────────────────┐
│                   BACKEND (Node.js + Express)                          │
│   API Gateway │ Session Manager │ Redis Cache                          │
│                                                                          │
│   Route Map:                                                             │
│   /predict   → ML Service                                                │
│   /explain   → ML Service                                                │
│   /simulate  → ML Service                                                │
│   /insights  → Lightweight LLM                                           │
│   /chat      → Agent Service                                             │
└──────┬──────────────────────────────────────────┬───────────────────────┘
       │ REST                                      │ REST
┌──────▼──────────────┐               ┌───────────▼────────────────────┐
│  ML MICROSERVICE    │               │  LIGHTWEIGHT INSIGHTS SERVICE   │
│  Python + FastAPI   │               │  Summary Generation             │
│  XGBoost + SHAP     │               │  /insights                      │
│  /predict           │               └────────────────────────────────┘
│  /explain           │
│  /simulate          │
└──────┬──────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────────────┐
│                    AGENT SERVICE (Python — LangGraph)                   │
│   Chat-only reasoning path (/chat)                                      │
│   Input Parser → Planner → Tool Executor → Memory Node → Synthesizer    │
│   Agent may call: ML Service + RAG Service                              │
└──────┬───────────────────────────────────────────────┬──────────────────┘
       │ REST                                          │ REST
┌──────▼──────────────────────────┐        ┌───────────▼───────────────────┐
│  ML SERVICE (internal reuse)    │        │  RAG SERVICE (Python/FastAPI) │
│  Used by Agent for deep chat    │        │  Pinecone + LangChain Embed   │
└─────────────────────────────────┘        │  WHO/CDC/Mobility Docs        │
                                           │  /retrieve                    │
                                           └───────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                   │
│  processed_data.csv / SQLite │ Johns Hopkins + OWID + Mobility         │
│  Feature Store (precomputed)                                           │
└────────────────────────────────────────────────────────────────────────┘
```

**Key corrections from original:**

- Real-time analytics routes (`/predict`, `/explain`, `/simulate`) go **directly to ML service**.
- Agent is used **only for `/chat` and deep reasoning**.
- `/insights` is a **new lightweight summary layer** for fast UI-facing explanations.
- RAG remains a separate service, but is used **only inside the agent flow** (not UI updates).

---

## 🧩 User Interaction Flow (Updated)

1. Region click → Backend calls ML directly (`/predict`, `/explain`)
2. Slider change → Backend calls ML `/simulate`
3. Insights panel → Backend calls lightweight `/insights`
4. Chat query → Backend calls Agent (`/chat`), which can combine ML + RAG

---

## 🧠 Insights Layer (NEW)

- Purpose: quick summaries and slider-impact explanations
- Input: forecast, shap, simulation
- Output: short bullet insights
- RAG usage: none (RAG is not called from insights)

---

## 🤖 Agent Role (Updated)

Agent is now responsible only for:

- Chat-based reasoning
- Combining ML + RAG during deep analysis

Agent is not used for:

- UI updates
- Slider interactions
- Basic summary generation

---

## 📁 Full Project Folder Structure

```
epidemic-intelligence/
├── frontend/                   # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx          # Leaflet choropleth risk map
│   │   │   ├── ForecastChart.jsx    # Recharts line chart (actual vs predicted)
│   │   │   ├── ScenarioSliders.jsx  # mobility/vaccination sliders → simulate
│   │   │   ├── ChatUI.jsx           # Agent chat interface
│   │   │   ├── RiskBadge.jsx        # Low/Medium/High pill component
│   │   │   └── SHAPBar.jsx          # Horizontal bar chart for SHAP values
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx        # Main layout combining all components
│   │   │   └── RegionDetail.jsx     # Per-region deep-dive
│   │   ├── hooks/
│   │   │   ├── useForecast.js       # React Query hook for /predict
│   │   │   └── useAgent.js          # WebSocket or polling hook for /chat
│   │   ├── store/
│   │   │   └── appStore.js          # Zustand global state (selectedRegion, chatHistory)
│   │   ├── api/
│   │   │   └── client.js            # Axios instance with base URL + interceptors
│   │   └── App.jsx
│   ├── package.json
│   └── .env                         # REACT_APP_BACKEND_URL=http://localhost:3001
│
├── backend/                    # Node.js Express (API Gateway + Cache)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── predict.js           # POST /api/predict → checks Redis → calls ML service
│   │   │   ├── chat.js              # POST /api/chat → calls agent service
│   │   │   ├── explain.js           # POST /api/explain → checks Redis → calls ML service
│   │   │   ├── simulate.js          # POST /api/simulate → calls ML service (no cache)
│   │   │   └── insights.js          # POST /api/insights → lightweight LLM summaries
│   │   ├── middleware/
│   │   │   ├── cache.js             # Redis get/set middleware
│   │   │   └── errorHandler.js
│   │   ├── services/
│   │   │   ├── mlService.js         # Axios calls to FastAPI ML (port 8001)
│   │   │   ├── agentService.js      # Axios calls to agent FastAPI (port 8002)
│   │   │   ├── insightsService.js   # Axios calls to lightweight insights service
│   │   │   └── ragService.js        # Used by agent path; not used for UI routes
│   │   ├── utils/
│   │   │   └── redis.js             # Redis client + helper functions
│   │   └── index.js                 # Express app entry, route mounting
│   ├── package.json
│   └── .env                         # ML_URL, AGENT_URL, RAG_URL, INSIGHTS_URL, REDIS_URL
│
├── ml-service/                 # FastAPI — XGBoost + SHAP
│   ├── app/
│   │   ├── main.py                  # FastAPI app, mount routers
│   │   ├── routers/
│   │   │   ├── predict.py           # POST /predict
│   │   │   ├── explain.py           # POST /explain
│   │   │   └── simulate.py          # POST /simulate
│   │   ├── models/
│   │   │   ├── xgb_forecast.pkl     # Saved XGBoost regressor
│   │   │   └── xgb_risk.pkl         # Saved XGBoost classifier
│   │   ├── ml/
│   │   │   ├── feature_engineering.py   # All feature computation
│   │   │   ├── train.py                 # Training script (run once)
│   │   │   └── shap_explainer.py        # SHAP explainer wrapper
│   │   ├── data/
│   │   │   ├── raw/                     # Downloaded CSVs
│   │   │   └── processed/
│   │   │       └── features.csv         # Final feature matrix
│   │   └── schemas.py               # Pydantic request/response models
│   ├── requirements.txt
│   └── .env
│
├── rag-service/                # FastAPI — Pinecone + Embeddings
│   ├── app/
│   │   ├── main.py                  # FastAPI app
│   │   ├── routers/
│   │   │   └── retrieve.py          # POST /retrieve
│   │   ├── ingestion/
│   │   │   ├── ingest_docs.py       # Load, chunk, embed, upsert to Pinecone
│   │   │   └── sources.py           # List of document URLs/files
│   │   ├── retrieval/
│   │   │   └── retriever.py         # Query Pinecone, return top-k chunks
│   │   └── schemas.py
│   ├── requirements.txt
│   └── .env                         # PINECONE_API_KEY, PINECONE_INDEX, OPENAI_API_KEY
│
└── agent/                      # LangGraph Agent (Python FastAPI wrapper)
    ├── app/
    │   ├── main.py                  # FastAPI exposing POST /agent/chat
    │   ├── graph/
    │   │   ├── state.py             # AgentState TypedDict
    │   │   ├── nodes.py             # All node functions
    │   │   ├── edges.py             # Conditional routing logic
    │   │   └── build_graph.py       # Compile the StateGraph
    │   ├── tools/
    │   │   ├── registry.py          # Tool registry dict
    │   │   ├── forecast_tool.py
    │   │   ├── explain_tool.py
    │   │   ├── simulate_tool.py
    │   │   └── rag_tool.py
    │   └── schemas.py
    ├── requirements.txt
    └── .env                         # ML_URL, RAG_URL, OPENAI_API_KEY
```

---

## 🤖 LangGraph Agent — Deep Dive

### State Object (the "brain" passed between nodes)

```python
# agent/app/graph/state.py
from typing import TypedDict, List, Optional, Dict, Any

class AgentState(TypedDict):
    # INPUT
    user_query: str                    # Raw user question
    region: Optional[str]              # Extracted region (e.g. "Italy")
  mode: str                          # "chat" | "summary"
  context: Optional[Dict]            # Optional precomputed ML data from backend

    # PLANNING
    plan: List[str]                    # Ordered list of tool names to call
    current_step: int                  # Which step in plan we're at

    # TOOL OUTPUTS
    forecast_result: Optional[Dict]    # From forecast_tool
    explain_result: Optional[Dict]     # From explain_tool
    simulate_result: Optional[Dict]    # From simulate_tool
    rag_context: Optional[str]         # Retrieved document chunks (raw text)

    # MEMORY
    conversation_history: List[Dict]   # [{role, content}, ...]

    # OUTPUT
    final_answer: Optional[str]        # LLM-synthesized response
    error: Optional[str]               # Any error message
```

### Node Definitions

```python
# agent/app/graph/nodes.py

# ── NODE 1: Input Parser ─────────────────────────────────────────────
def input_parser_node(state: AgentState) -> AgentState:
    """
    Uses LLM to extract structured intent from free-form query.
    Fills: state["region"], validates query is epidemiological.
    """
    prompt = f"""
    Extract from this query:
    1. Region/country mentioned (or "global")
    2. Primary intent: forecast | explain | simulate | general_info

    Query: {state["user_query"]}
    Respond in JSON: {{"region": "...", "intent": "..."}}
    """
    response = llm.invoke(prompt)
    parsed = json.loads(response.content)
    state["region"] = parsed["region"]
    state["_intent"] = parsed["intent"]
    return state

# ── NODE 2: Planner ───────────────────────────────────────────────────
def planner_node(state: AgentState) -> AgentState:
    """
    Converts intent into an ordered tool execution plan.
    Rules (deterministic, no LLM needed):
      - "explain" intent → ["forecast", "explain", "rag"]
      - "simulate" intent → ["simulate", "rag"]
      - "forecast" intent → ["forecast", "rag"]
      - "general_info" → ["rag"]
    """
    intent_to_plan = {
        "explain":      ["forecast", "explain", "rag"],
        "simulate":     ["simulate", "rag"],
        "forecast":     ["forecast", "rag"],
        "general_info": ["rag"],
    }
    state["plan"] = intent_to_plan.get(state["_intent"], ["forecast", "rag"])
    state["current_step"] = 0
    return state

# ── NODE 3: Tool Executor ─────────────────────────────────────────────
def tool_executor_node(state: AgentState) -> AgentState:
    """
    Executes ONE tool from the plan at current_step.
    Reuses provided context when available; otherwise calls tool function.
    """
    tool_name = state["plan"][state["current_step"]]
    tool_fn = TOOL_REGISTRY[tool_name]

    context_key_map = {
        "forecast": "forecast_result",
        "explain":  "explain_result",
        "simulate": "simulate_result",
    }

    if state.get("context") and tool_name in context_key_map:
        result = state["context"].get(context_key_map[tool_name])
    else:
        result = tool_fn(region=state["region"], state=state)

    # Store result in the right state key
    result_key_map = {
        "forecast": "forecast_result",
        "explain":  "explain_result",
        "simulate": "simulate_result",
        "rag":      "rag_context",
    }
    state[result_key_map[tool_name]] = result
    state["current_step"] += 1
    return state

# ── NODE 4: Memory Manager ────────────────────────────────────────────
def memory_manager_node(state: AgentState) -> AgentState:
    """
    Appends the current turn to conversation history.
    Trims to last 10 turns to avoid context overflow.
    """
    state["conversation_history"].append({
        "role": "user",
        "content": state["user_query"]
    })
    state["conversation_history"] = state["conversation_history"][-10:]
    return state

# ── NODE 5: Response Synthesizer ─────────────────────────────────────
def synthesizer_node(state: AgentState) -> AgentState:
    """
    Assembles all tool results + RAG context and calls LLM
    to produce a final, scientifically grounded answer.
    """
    context_parts = []

    if state.get("forecast_result"):
        f = state["forecast_result"]
        context_parts.append(
            f"FORECAST DATA for {state['region']}:\n"
            f"7-day predicted cases: {f['forecast']}\n"
            f"Risk level: {f['risk_level']}"
        )

    if state.get("explain_result"):
        e = state["explain_result"]
        context_parts.append(
            f"KEY DRIVERS (SHAP):\n"
            f"Increasing risk: {e['top_positive']}\n"
            f"Decreasing risk: {e['top_negative']}"
        )

    if state.get("rag_context"):
        context_parts.append(
            f"RELEVANT PUBLIC HEALTH GUIDELINES:\n{state['rag_context']}"
        )

    system_prompt = """You are an epidemic intelligence analyst.
    Use ONLY the provided data to answer.
    Structure your answer as:
    1. Current situation summary
    2. Why this is happening (cite SHAP drivers)
    3. What the evidence says (cite guidelines)
    4. Recommended actions
    Never fabricate statistics."""

    user_message = (
        f"Question: {state['user_query']}\n\n"
        f"Data:\n" + "\n\n".join(context_parts)
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])

    state["final_answer"] = response.content
    return state
```

### RAG Usage Policy (Updated)

- RAG is used only inside agent chat/reasoning flow.
- RAG is not used for region-click UI updates, slider simulations, or `/insights` summaries.

### Graph Edges (Routing Logic)

```python
# agent/app/graph/edges.py

def should_continue_tools(state: AgentState) -> str:
    """
    After tool_executor: check if more tools remain in the plan.
    Returns: "continue" → tool_executor again | "synthesize" → synthesizer
    """
    if state["current_step"] < len(state["plan"]):
        return "continue"
    return "synthesize"

# agent/app/graph/build_graph.py
from langgraph.graph import StateGraph, END

def build_agent_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_parser",    input_parser_node)
    graph.add_node("memory_manager",  memory_manager_node)
    graph.add_node("planner",         planner_node)
    graph.add_node("tool_executor",   tool_executor_node)
    graph.add_node("synthesizer",     synthesizer_node)

    # Entry point
    graph.set_entry_point("input_parser")

    # Edges
    graph.add_edge("input_parser",   "memory_manager")
    graph.add_edge("memory_manager", "planner")
    graph.add_edge("planner",        "tool_executor")

    # Conditional: loop tools or go to synthesizer
    graph.add_conditional_edges(
        "tool_executor",
        should_continue_tools,
        {
            "continue":    "tool_executor",
            "synthesize":  "synthesizer",
        }
    )

    graph.add_edge("synthesizer", END)

    return graph.compile()
```

### Execution Trace: "Why is Italy high risk next week and what should we do?"

```
Step 1: input_parser_node
  IN:  user_query = "Why is Italy high risk next week and what should we do?"
  LLM extracts: region="Italy", intent="explain"
  OUT: state.region="Italy", state._intent="explain"

Step 2: memory_manager_node
  Appends user query to conversation_history

Step 3: planner_node
  intent="explain" → plan=["forecast", "explain", "rag"]
  current_step=0

Step 4: tool_executor_node (step 0 → "forecast")
  Calls: forecast_tool(region="Italy")
  HTTP POST http://localhost:8001/predict {"region":"Italy","days":7}
  Returns: {"forecast":[14200,15100,16800,...], "risk_level":"High"}
  state.forecast_result = {...}
  current_step=1

Step 5: tool_executor_node (step 1 → "explain")
  Calls: explain_tool(region="Italy")
  HTTP POST http://localhost:8001/explain {"region":"Italy"}
  Returns: {"top_positive":[{"feature":"mobility_retail","impact":0.41},...],
            "top_negative":[{"feature":"vaccination_rate","impact":-0.28},...]}
  state.explain_result = {...}
  current_step=2

Step 6: tool_executor_node (step 2 → "rag")
  Calls: rag_tool(query="Italy high risk outbreak intervention strategies")
  HTTP POST http://localhost:8003/retrieve {"query":"...","top_k":4}
  Returns: 4 chunks from WHO/CDC guidelines
  state.rag_context = "Chunk1: WHO recommends... Chunk2: Mobility restrictions..."
  current_step=3

Step 7: should_continue_tools → 3 >= 3 → "synthesize"

Step 8: synthesizer_node
  Assembles all state data, calls GPT-4o
  Produces structured answer:
    1. Italy is trending HIGH (16,800 cases projected by day 7)
    2. Key driver: retail mobility +41% above baseline (SHAP)
    3. Low vaccination uptake reducing herd immunity buffer (SHAP)
    4. WHO guidelines recommend targeted mobility restrictions...
    5. Recommended: Immediate retail hour restrictions + vaccination push

FINAL: state.final_answer = "Based on our model..."
```

---

## 🔧 Tool Registry — Strict Contract Design

```python
# agent/app/tools/registry.py
TOOL_REGISTRY = {
    "forecast": forecast_tool,
    "explain":  explain_tool,
    "simulate": simulate_tool,
    "rag":      rag_tool,
}
```

### Tool 1: forecast_tool

```
Function: forecast_tool(region: str, state: AgentState) -> dict

Input JSON:
{
  "region": "Italy",     # string, country/region name
  "days": 7              # int, forecast horizon (default 7)
}

Output JSON:
{
  "region": "Italy",
  "forecast": [14200, 15100, 16300, 16800, 17100, 17400, 17600],  # list[int]
  "risk_level": "High",          # "Low" | "Medium" | "High"
  "confidence_interval": {
    "lower": [13000, 14200, ...],
    "upper": [15400, 16000, ...]
  },
  "last_actual_cases": 13800,
  "as_of_date": "2024-01-15"
}

Backend mapping: POST http://ml-service:8001/predict
```

### Tool 2: explain_tool

```
Function: explain_tool(region: str, state: AgentState) -> dict

Input JSON:
{
  "region": "Italy"
}

Output JSON:
{
  "region": "Italy",
  "top_positive": [
    {"feature": "mobility_retail_and_recreation", "impact": 0.41, "value": 0.23},
    {"feature": "lag_7_cases", "impact": 0.29, "value": 14800},
    {"feature": "growth_rate_7d", "impact": 0.18, "value": 0.08}
  ],
  "top_negative": [
    {"feature": "vaccination_rate", "impact": -0.28, "value": 0.62},
    {"feature": "stringency_index", "impact": -0.11, "value": 45.0}
  ],
  "base_value": 8200.0,
  "prediction": 16300.0
}

Backend mapping: POST http://ml-service:8001/explain
```

### Tool 3: simulate_tool

```
Function: simulate_tool(region: str, state: AgentState, params: dict) -> dict

Input JSON:
{
  "region": "Italy",
  "interventions": {
    "mobility_change": -0.20,        # -20% mobility reduction
    "vaccination_change": 0.10,      # +10% vaccination rate
    "stringency_change": 0.15        # +15% stringency
  },
  "days": 14
}

Output JSON:
{
  "baseline_forecast": [16800, 17100, 17400, ...],
  "simulated_forecast": [14100, 13200, 12800, ...],
  "cases_averted": 18500,
  "peak_delay_days": 5,
  "intervention_summary": "20% mobility reduction + 10% vaccination increase"
}

Backend mapping: POST http://ml-service:8001/simulate
```

### Tool 4: rag_tool

```
Function: rag_tool(query: str, state: AgentState) -> str

Input JSON:
{
  "query": "Italy outbreak intervention mobility restriction",
  "top_k": 4,
  "filter": {
    "source_type": ["WHO", "CDC", "research_paper"]
  }
}

Output: str (concatenated relevant chunks with source labels)
  "[WHO Guidelines, 2023-01]: When case growth rate exceeds 8%...
   [CDC Recommendation, 2023-06]: Mobility interventions show..."

Backend mapping: POST http://rag-service:8003/retrieve
```

---

## 🔬 ML Pipeline — Full Detail

### Step 1: Data Ingestion

```python
# ml-service/app/ml/feature_engineering.py

import pandas as pd
import numpy as np

def load_jhu_data() -> pd.DataFrame:
    """
    Load Johns Hopkins confirmed cases.
    Source: GitHub raw CSV
    """
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
    df = pd.read_csv(url)

    # Melt wide format (one col per date) → long format (date column)
    id_cols = ["Province/State", "Country/Region", "Lat", "Long"]
    df = df.melt(id_vars=id_cols, var_name="date", value_name="confirmed_cases")
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby(["Country/Region", "date"])["confirmed_cases"].sum().reset_index()
    df.rename(columns={"Country/Region": "region"}, inplace=True)
    return df

def load_owid_data() -> pd.DataFrame:
    """
    Load Our World in Data vaccination + testing.
    """
    url = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"
    df = pd.read_csv(url, usecols=[
        "location", "date",
        "people_vaccinated_per_hundred",
        "total_tests_per_thousand",
        "stringency_index",
        "hosp_patients_per_million"
    ])
    df["date"] = pd.to_datetime(df["date"])
    df.rename(columns={"location": "region"}, inplace=True)
    return df

def load_mobility_data(filepath: str) -> pd.DataFrame:
    """
    Load Google Mobility (manually downloaded CSV).
    Aggregate mobility categories into a single mobility_index.
    """
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    mobility_cols = [
        "retail_and_recreation_percent_change_from_baseline",
        "grocery_and_pharmacy_percent_change_from_baseline",
        "transit_stations_percent_change_from_baseline",
        "workplaces_percent_change_from_baseline",
    ]
    df["mobility_index"] = df[mobility_cols].mean(axis=1) / 100.0
    return df[["country_region", "date", "mobility_index",
               "retail_and_recreation_percent_change_from_baseline"]]
```

### Step 2: Feature Engineering (Explicit Formulas)

```python
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    df must have columns: region, date, confirmed_cases
    (after merging with OWID and mobility)
    """
    df = df.sort_values(["region", "date"])

    # ── Lag Features ─────────────────────────────────────────────────
    # Converts time-series to tabular by shifting target back N days.
    # XGBoost sees: "given cases at T-1, T-7, predict cases at T+7"
    df["lag_1"]  = df.groupby("region")["confirmed_cases"].shift(1)
    df["lag_7"]  = df.groupby("region")["confirmed_cases"].shift(7)
    df["lag_14"] = df.groupby("region")["confirmed_cases"].shift(14)

    # ── Rolling Statistics ────────────────────────────────────────────
    df["rolling_mean_7"]  = (
        df.groupby("region")["confirmed_cases"]
          .transform(lambda x: x.shift(1).rolling(7).mean())
    )
    df["rolling_std_7"]   = (
        df.groupby("region")["confirmed_cases"]
          .transform(lambda x: x.shift(1).rolling(7).std())
    )

    # ── Growth Rate ───────────────────────────────────────────────────
    # growth_rate = (cases_t - cases_{t-7}) / (cases_{t-7} + 1)
    df["growth_rate_7d"] = (
        (df["confirmed_cases"] - df["lag_7"]) / (df["lag_7"] + 1)
    )

    # ── Epidemiological Features ──────────────────────────────────────
    # cases_per_100k requires population lookup (hardcoded dict or merge)
    POPULATION = {"Italy": 60_000_000, "India": 1_400_000_000, ...}
    df["population"] = df["region"].map(POPULATION)
    df["cases_per_100k"] = df["confirmed_cases"] / (df["population"] / 100_000)

    # ── Target Variable ───────────────────────────────────────────────
    # Predict cases 7 days ahead (shift back by -7)
    df["target_cases_7d"] = df.groupby("region")["confirmed_cases"].shift(-7)

    # ── Risk Label (for classifier) ───────────────────────────────────
    # High:   growth_rate > 0.10 (10% weekly increase)
    # Medium: growth_rate 0.02–0.10
    # Low:    growth_rate < 0.02
    def label_risk(row):
        if row["growth_rate_7d"] > 0.10: return "High"
        elif row["growth_rate_7d"] > 0.02: return "Medium"
        else: return "Low"
    df["risk_label"] = df.apply(label_risk, axis=1)

    # Drop rows with NaN targets (future or lag gaps)
    df = df.dropna(subset=["target_cases_7d", "lag_7", "rolling_mean_7"])

    return df

FEATURE_COLS = [
    "lag_1", "lag_7", "lag_14",
    "rolling_mean_7", "rolling_std_7",
    "growth_rate_7d",
    "cases_per_100k",
    "people_vaccinated_per_hundred",
    "stringency_index",
    "mobility_index",
    "retail_and_recreation_percent_change_from_baseline",
    "total_tests_per_thousand",
]
```

### Step 3: Training Pipeline

```python
# ml-service/app/ml/train.py
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, f1_score
import shap, pickle

def train_and_save():
    # 1. Load processed features
    df = pd.read_csv("data/processed/features.csv")

    X = df[FEATURE_COLS]
    y_reg = df["target_cases_7d"]
    y_cls = df["risk_label"]

    # 2. Time-series split (NEVER random split — data leakage!)
    tscv = TimeSeriesSplit(n_splits=5)

    # 3. Train regressor
    reg_params = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "reg:squarederror",
        "tree_method": "hist",   # fast on CPU
        "random_state": 42
    }
    model_reg = xgb.XGBRegressor(**reg_params)
    model_reg.fit(X, y_reg)
    rmse = np.sqrt(mean_squared_error(y_reg, model_reg.predict(X)))
    print(f"Train RMSE: {rmse:.2f}")

    # 4. Train classifier
    model_cls = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, use_label_encoder=False,
        eval_metric="mlogloss", random_state=42
    )
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    model_cls.fit(X, le.fit_transform(y_cls))

    # 5. SHAP explainer (TreeExplainer is fast for XGBoost)
    explainer = shap.TreeExplainer(model_reg)

    # 6. Save artifacts
    with open("models/xgb_forecast.pkl", "wb") as f:
        pickle.dump(model_reg, f)
    with open("models/xgb_risk.pkl", "wb") as f:
        pickle.dump({"model": model_cls, "encoder": le}, f)
    with open("models/shap_explainer.pkl", "wb") as f:
        pickle.dump(explainer, f)

    print("✅ Models saved.")
```

### Step 4: FastAPI ML Service (Full)

```python
# ml-service/app/main.py
from fastapi import FastAPI
from app.routers import predict, explain, simulate
import pickle

app = FastAPI(title="Epidemic ML Service", version="1.0")
app.include_router(predict.router, prefix="/predict")
app.include_router(explain.router, prefix="/explain")
app.include_router(simulate.router, prefix="/simulate")

@app.on_event("startup")
async def load_models():
    app.state.model_reg  = pickle.load(open("models/xgb_forecast.pkl",  "rb"))
    app.state.model_cls  = pickle.load(open("models/xgb_risk.pkl",      "rb"))
    app.state.explainer  = pickle.load(open("models/shap_explainer.pkl","rb"))
    app.state.features   = pd.read_csv("data/processed/features.csv")
    print("✅ Models loaded")

# ml-service/app/routers/predict.py
from fastapi import APIRouter, Request
from app.schemas import PredictRequest, PredictResponse

router = APIRouter()

@router.post("", response_model=PredictResponse)
def predict_endpoint(body: PredictRequest, request: Request):
    model   = request.app.state.model_reg
    df      = request.app.state.features

    region_df = df[df["region"] == body.region].sort_values("date")
    if region_df.empty:
        raise HTTPException(404, f"Region '{body.region}' not found")

    latest = region_df.iloc[-1]
    X_input = latest[FEATURE_COLS].values.reshape(1, -1)

    # Predict next 7 days by recursive 1-step forecasting
    forecasts = []
    current_row = latest.copy()
    for day in range(body.days):
        X = current_row[FEATURE_COLS].values.reshape(1, -1)
        pred = float(model.predict(X)[0])
        forecasts.append(int(pred))
        # Shift lags for next iteration
        current_row["lag_14"] = current_row["lag_7"]
        current_row["lag_7"]  = current_row["lag_1"]
        current_row["lag_1"]  = pred
        current_row["rolling_mean_7"] = np.mean(forecasts[-7:]) if len(forecasts) >= 7 else np.mean(forecasts)

    # Risk classification on current features
    cls_model = request.app.state.model_cls
    risk_encoded = cls_model["model"].predict(X_input)[0]
    risk_label   = cls_model["encoder"].inverse_transform([risk_encoded])[0]

    return PredictResponse(
        region=body.region,
        forecast=forecasts,
        risk_level=risk_label,
        last_actual_cases=int(latest["confirmed_cases"]),
        as_of_date=str(latest["date"])
    )

# ml-service/app/schemas.py
from pydantic import BaseModel
from typing import List

class PredictRequest(BaseModel):
    region: str
    days: int = 7

class PredictResponse(BaseModel):
    region: str
    forecast: List[int]
    risk_level: str
    last_actual_cases: int
    as_of_date: str
```

---

## 📚 RAG Pipeline — Production Level

### Document Sources

```python
# rag-service/app/ingestion/sources.py
DOCUMENT_SOURCES = [
    # WHO guidelines PDFs (download and place in docs/)
    {"path": "docs/who_epidemic_response_2023.pdf", "source": "WHO", "type": "guideline"},
    {"path": "docs/cdc_outbreak_management.pdf",    "source": "CDC", "type": "guideline"},
    # Web URLs (fetched at ingestion time)
    {"url": "https://www.who.int/docs/default-source/coronaviruse/situation-reports/",
     "source": "WHO", "type": "situation_report"},
    # Research papers (manual PDFs)
    {"path": "docs/mobility_transmission_study.pdf", "source": "research", "type": "paper"},
]
```

### Chunking Strategy

```python
# rag-service/app/ingestion/ingest_docs.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
import PyPDF2, uuid

def chunk_document(text: str, metadata: dict) -> list:
    """
    Chunk strategy: 500 tokens, 50 overlap.
    Why: 500 tokens fits in LLM context without truncation.
         50 token overlap preserves sentence context at chunk boundaries.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ". ", " "]  # paragraph > sentence > word
    )
    chunks = splitter.split_text(text)
    return [
        {
            "id":       str(uuid.uuid4()),
            "text":     chunk,
            "metadata": {
                **metadata,
                "chunk_index": i,
                "char_count":  len(chunk),
            }
        }
        for i, chunk in enumerate(chunks)
    ]

def ingest_all():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")  # 1536-dim, cheap

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = "epidemic-rag"

    # Create index if not exists
    if index_name not in [i.name for i in pc.list_indexes()]:
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

    index = pc.Index(index_name)

    for source in DOCUMENT_SOURCES:
        text = extract_text(source)  # PDF or URL fetch
        chunks = chunk_document(text, {
            "source":      source.get("source"),
            "source_type": source.get("type"),
            "doc_name":    source.get("path", source.get("url", ""))[:80]
        })

        # Batch embed (Pinecone limit: 100 vectors per upsert)
        for batch_start in range(0, len(chunks), 100):
            batch = chunks[batch_start:batch_start + 100]
            texts  = [c["text"] for c in batch]
            embeds = embeddings.embed_documents(texts)

            vectors = [
                (c["id"], embed, c["metadata"])
                for c, embed in zip(batch, embeds)
            ]
            index.upsert(vectors=vectors)

        print(f"✅ Ingested: {source.get('source')} — {len(chunks)} chunks")
```

### Pinecone Index Structure

```
Index name:  epidemic-rag
Dimension:   1536 (text-embedding-3-small)
Metric:      cosine
Metadata schema per vector:
  {
    "source":      "WHO" | "CDC" | "research",
    "source_type": "guideline" | "situation_report" | "paper",
    "doc_name":    str,
    "chunk_index": int,
    "char_count":  int
  }
```

### Retrieval Endpoint

```python
# rag-service/app/routers/retrieve.py
from fastapi import APIRouter
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from app.schemas import RetrieveRequest, RetrieveResponse

router = APIRouter()

@router.post("", response_model=RetrieveResponse)
def retrieve(body: RetrieveRequest):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vec  = embeddings.embed_query(body.query)

    pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("epidemic-rag")

    # Metadata filter: only retrieve from authoritative sources
    filter_dict = {}
    if body.filter:
        filter_dict = {"source_type": {"$in": body.filter.get("source_type", [])}}

    results = index.query(
        vector=query_vec,
        top_k=body.top_k,          # default 4
        include_metadata=True,
        filter=filter_dict or None
    )

    # Format output: "[SOURCE, doc_name]: chunk_text"
    context_parts = []
    for match in results["matches"]:
        meta = match["metadata"]
        chunk = match.get("metadata", {}).get("text", "")  # store text in metadata too
        context_parts.append(
            f"[{meta['source']}, {meta['doc_name'][:40]}]: {chunk}"
        )

    return RetrieveResponse(
        context="\n\n".join(context_parts),
        num_chunks=len(context_parts),
        sources=[m["metadata"]["source"] for m in results["matches"]]
    )
```

> **Note:** Store the chunk `text` field in Pinecone metadata so retrieval returns text directly. Pinecone metadata max is 40KB per vector — keep chunk text under 2000 chars.

---

## 🌐 Backend (Node.js) — API Gateway

### How to Start

```bash
cd backend
npm install
# Set .env:
# ML_URL=http://localhost:8001
# AGENT_URL=http://localhost:8002
# RAG_URL=http://localhost:8003
# REDIS_URL=redis://localhost:6379
npm run dev     # uses nodemon
```

### Route Architecture

```javascript
// backend/src/index.js
const express = require("express");
const cors = require("cors");
const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/predict", require("./routes/predict"));
app.use("/api/explain", require("./routes/explain"));
app.use("/api/simulate", require("./routes/simulate"));
app.use("/api/chat", require("./routes/chat"));

app.listen(3001, () => console.log("Backend running on :3001"));

// backend/src/routes/predict.js
const router = require("express").Router();
const { getCache, setCache } = require("../utils/redis");
const mlService = require("../services/mlService");

router.post("/", async (req, res) => {
  const { region, days = 7 } = req.body;
  const cacheKey = `predict:${region}:${days}`;

  // 1. Check Redis cache (TTL: 1 hour — data doesn't change that fast)
  const cached = await getCache(cacheKey);
  if (cached) return res.json({ ...cached, cached: true });

  // 2. Call ML service
  const result = await mlService.predict({ region, days });

  // 3. Cache result
  await setCache(cacheKey, result, 3600);

  res.json(result);
});

module.exports = router;

// backend/src/utils/redis.js
const redis = require("redis");
const client = redis.createClient({ url: process.env.REDIS_URL });
client.connect();

async function getCache(key) {
  const val = await client.get(key);
  return val ? JSON.parse(val) : null;
}

async function setCache(key, value, ttlSeconds = 3600) {
  await client.setEx(key, ttlSeconds, JSON.stringify(value));
}

module.exports = { getCache, setCache };
```

### Redis Caching Strategy

| Route       | Cache Key                 | TTL    | Notes                  |
| ----------- | ------------------------- | ------ | ---------------------- |
| `/predict`  | `predict:{region}:{days}` | 1 hour | Data refreshes daily   |
| `/explain`  | `explain:{region}`        | 1 hour | SHAP values stable     |
| `/simulate` | ❌ No cache               | —      | User-specific params   |
| `/chat`     | ❌ No cache               | —      | Always fresh reasoning |

---

## 🎨 Frontend (React) — Component Map

### How to Start

```bash
cd frontend
npm install
echo "REACT_APP_BACKEND_URL=http://localhost:3001" > .env
npm start
```

### Component Hierarchy

```
App.jsx
└── Dashboard.jsx
    ├── MapView.jsx              ← Leaflet choropleth, color = risk_level
    │   └── RiskBadge.jsx        ← Color pill overlay per region
    ├── ForecastChart.jsx        ← Recharts LineChart (actual + predicted)
    ├── SHAPBar.jsx              ← Horizontal BarChart, red=positive, green=negative
    ├── ScenarioSliders.jsx      ← Sliders → /api/simulate → re-render chart
    └── ChatUI.jsx               ← Input box + message list → /api/chat
```

### Key Implementation Patterns

```jsx
// frontend/src/hooks/useForecast.js
import { useQuery } from "@tanstack/react-query";
import api from "../api/client";

export function useForecast(region) {
  return useQuery({
    queryKey: ["forecast", region],
    queryFn: () =>
      api.post("/predict", { region, days: 7 }).then((r) => r.data),
    enabled: !!region,
    staleTime: 1000 * 60 * 30, // 30 min — matches Redis TTL
  });
}

// frontend/src/components/ChatUI.jsx
function ChatUI() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  async function send() {
    const userMsg = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const res = await api.post("/chat", { message: input });
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: res.data.answer },
    ]);
  }

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, i) => (
          <ChatMessage key={i} {...m} />
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
      />
      <button onClick={send}>Ask</button>
    </div>
  );
}
```

---

## 🏆 Bonus Winning Features

### Feature 1: Scenario Simulation Engine

The sliders on the frontend (mobility_change, vaccination_change) call `/simulate`. The ML service creates a modified feature row from the latest real data, applies the delta, and runs the XGBoost regressor to show "what would happen if...".

```python
# ml-service/app/routers/simulate.py
@router.post("")
def simulate(body: SimulateRequest, request: Request):
    model = request.app.state.model_reg
    df    = request.app.state.features

    latest = df[df["region"] == body.region].sort_values("date").iloc[-1].copy()

    # Apply intervention deltas
    latest["mobility_index"]                += body.interventions.get("mobility_change", 0)
    latest["people_vaccinated_per_hundred"] += body.interventions.get("vaccination_change", 0) * 100
    latest["stringency_index"]              += body.interventions.get("stringency_change", 0) * 100

    # Predict baseline (no intervention)
    X_base = df[df["region"]==body.region].sort_values("date").iloc[-1][FEATURE_COLS].values.reshape(1,-1)
    baseline = [int(model.predict(X_base)[0])] * body.days  # simplified

    # Predict with intervention
    X_sim  = latest[FEATURE_COLS].values.reshape(1, -1)
    simmed = [int(model.predict(X_sim)[0])] * body.days    # simplified

    return SimulateResponse(
        baseline_forecast=baseline,
        simulated_forecast=simmed,
        cases_averted=sum(baseline) - sum(simmed)
    )
```

### Feature 2: Policy Recommendation Engine

After SHAP shows top drivers, the synthesizer node cross-references with RAG to generate WHO/CDC-aligned recommendations. The key is the **prompt template** in `synthesizer_node`:

```python
POLICY_PROMPT = """
Given these SHAP top drivers: {shap_drivers}
And these WHO/CDC guidelines: {rag_context}

Generate exactly 3 policy recommendations:
1. [Immediate — 0-3 days]: ...
2. [Short-term — 1-2 weeks]: ...
3. [Long-term — 1 month+]: ...

Each must cite the specific SHAP driver it addresses and the guideline source.
Format as JSON array: [{"timeline": "...", "action": "...", "driver": "...", "source": "..."}]
"""
```

### Feature 3: Risk Explanation Dashboard (SHAP Visual)

On the frontend, `SHAPBar.jsx` renders a waterfall-style bar chart where:

- Red bars = features pushing risk UP (positive SHAP)
- Green bars = features pushing risk DOWN (negative SHAP)
- Width = magnitude of impact

This is the single most impressive visual for judges because it makes the model **interpretable**.

```jsx
// frontend/src/components/SHAPBar.jsx
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip } from "recharts";

function SHAPBar({ explainData }) {
  const data = [
    ...explainData.top_positive.map((f) => ({ ...f, impact: +f.impact })),
    ...explainData.top_negative.map((f) => ({ ...f, impact: +f.impact })),
  ].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  return (
    <BarChart data={data} layout="vertical">
      <XAxis type="number" domain={[-0.5, 0.5]} />
      <YAxis dataKey="feature" type="category" width={200} />
      <Tooltip />
      <Bar dataKey="impact">
        {data.map((entry, i) => (
          <Cell key={i} fill={entry.impact > 0 ? "#ef4444" : "#22c55e"} />
        ))}
      </Bar>
    </BarChart>
  );
}
```

---

## 📅 5-Day Execution Plan (Micro-Steps)

---

### DAY 1 — Data Pipeline + ML Foundation

**Owner: ML Engineer**

#### Block 1 (9AM–11AM): Environment Setup

```bash
# 1. Create virtualenv
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install fastapi uvicorn xgboost shap pandas numpy scikit-learn pydantic python-dotenv

# 3. Create folder structure
mkdir -p ml-service/app/{routers,ml,models,data/{raw,processed}}
touch ml-service/app/{main.py,schemas.py}
touch ml-service/app/ml/{feature_engineering.py,train.py,shap_explainer.py}

# 4. Verify Python can download data
python -c "import pandas as pd; pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv').head()"
```

**Expected output:** DataFrame prints without error.

#### Block 2 (11AM–1PM): Data Ingestion + Merge

- Implement `load_jhu_data()`, `load_owid_data()` in `feature_engineering.py`
- Merge on `[region, date]` — use outer join, fill NaN with 0
- Save merged raw to `data/raw/merged_raw.csv`
- **Test:** `df["region"].unique()` shows 180+ countries

#### Block 3 (2PM–4PM): Feature Engineering

- Implement `engineer_features()` with all lag features, rolling stats, growth rate
- Run on full dataset, save to `data/processed/features.csv`
- **Test:** Check `features.csv` has columns: lag_1, lag_7, rolling_mean_7, growth_rate_7d, target_cases_7d, risk_label

#### Block 4 (4PM–6PM): Train XGBoost + Save

- Implement and run `train.py`
- Verify `models/` folder has: `xgb_forecast.pkl`, `xgb_risk.pkl`, `shap_explainer.pkl`
- **Test:** Load model, run prediction on Italy, get a number. Print RMSE.

---

### DAY 2 — FastAPI ML Service + SHAP + RAG Ingestion

**Owner: ML Engineer + Backend Dev**

#### Block 1 (9AM–11AM): Start FastAPI ML Service

```bash
cd ml-service
# Create main.py with startup model loading
# How to start:
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Test immediately:
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"region": "Italy", "days": 7}'
```

**Expected output:** JSON with `forecast` array and `risk_level`

#### Block 2 (11AM–1PM): /explain and /simulate Endpoints

- Implement SHAP endpoint: load `shap_explainer.pkl`, compute `shap_values` for latest region row
- Extract top 3 positive, top 3 negative contributors
- **Test:** `curl -X POST http://localhost:8001/explain -d '{"region":"Italy"}'`

#### Block 3 (2PM–4PM): RAG Service Setup

```bash
mkdir -p rag-service/app/{routers,ingestion,retrieval}
pip install langchain langchain-openai pinecone-client pypdf2

# Set env vars
export OPENAI_API_KEY=sk-...
export PINECONE_API_KEY=...

# Create index + ingest (run once)
python rag-service/app/ingestion/ingest_docs.py
```

- Download WHO/CDC PDFs manually (2–3 documents is enough for hackathon)
- **Test:** Check Pinecone dashboard → index exists with N vectors

#### Block 4 (4PM–6PM): RAG /retrieve Endpoint

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
curl -X POST http://localhost:8003/retrieve \
  -d '{"query":"mobility intervention outbreak control","top_k":3}'
```

**Expected output:** JSON with `context` field containing chunked guidelines text.

---

### DAY 3 — LangGraph Agent + Node.js Backend

**Owner: Backend Dev + AI Engineer**

#### Block 1 (9AM–11AM): LangGraph Agent Setup

```bash
mkdir -p agent/app/{graph,tools}
pip install langgraph langchain-openai

# Build in order:
# 1. state.py — define AgentState TypedDict
# 2. tools/forecast_tool.py — HTTP call to :8001/predict
# 3. tools/explain_tool.py — HTTP call to :8001/explain
# 4. tools/rag_tool.py — HTTP call to :8003/retrieve
# 5. tools/registry.py — dict mapping name → function
# 6. graph/nodes.py — all 5 node functions
# 7. graph/edges.py — should_continue_tools
# 8. graph/build_graph.py — compile graph
```

#### Block 2 (11AM–1PM): Test Agent Locally (NO FastAPI yet)

```python
# Quick test script: agent/test_agent.py
from app.graph.build_graph import build_agent_graph
from app.graph.state import AgentState

graph = build_agent_graph()
result = graph.invoke({
    "user_query": "Why is Italy high risk next week?",
    "conversation_history": [],
    "plan": [], "current_step": 0,
    # rest are None
})
print(result["final_answer"])
```

**Expected output:** Multi-paragraph structured answer. Fix any errors before wrapping in FastAPI.

#### Block 3 (2PM–4PM): Agent FastAPI Wrapper

```python
# agent/app/main.py
@app.post("/agent/chat")
async def chat(body: ChatRequest):
    graph = build_agent_graph()
    result = graph.invoke({
        "user_query": body.message,
        "conversation_history": body.history or [],
        "plan": [], "current_step": 0,
        "forecast_result": None, "explain_result": None,
        "simulate_result": None, "rag_context": None,
        "final_answer": None, "error": None
    })
    return {"answer": result["final_answer"]}

# Start:
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### Block 4 (4PM–6PM): Node.js Backend

```bash
cd backend && npm init -y
npm install express cors axios redis dotenv

# Implement routes (predict, explain, simulate, chat)
# Implement Redis cache middleware
node src/index.js   # should print "Backend running on :3001"

# End-to-end test:
curl -X POST http://localhost:3001/api/predict \
  -H "Content-Type: application/json" \
  -d '{"region":"Italy"}'
# Should return forecast + log "cache miss" first time, "cache hit" second time
```

---

### DAY 4 — React Frontend + Integration

**Owner: Frontend Dev**

#### Block 1 (9AM–11AM): React Setup + API Client

```bash
npx create-react-app frontend --template typescript  # or plain JS
cd frontend && npm install axios @tanstack/react-query recharts leaflet react-leaflet zustand
```

```javascript
// src/api/client.js
import axios from "axios";
const api = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || "http://localhost:3001/api",
});
export default api;
```

#### Block 2 (11AM–1PM): Dashboard Layout + MapView

- Use `react-leaflet` with `GeoJSON` layer for country outlines
- Color countries by `risk_level` from `/predict` (red=High, yellow=Medium, green=Low)
- Click on country → triggers `selectedRegion` state update → other components react

#### Block 3 (2PM–4PM): ForecastChart + SHAPBar

- `ForecastChart`: Line chart with actual cases (historical) + predicted (dashed)
- `SHAPBar`: Horizontal bar with color coded by sign
- Wire to `useForecast(selectedRegion)` and `useExplain(selectedRegion)` hooks

#### Block 4 (4PM–6PM): ChatUI + ScenarioSliders

- ChatUI: Simple message list + input. POST to `/api/chat`, display `answer`
- ScenarioSliders: 3 sliders → state → debounced POST to `/api/simulate` → overlay simulated line on ForecastChart
- **Test:** Full end-to-end: select Italy on map → see forecast → open chat → ask "Why is Italy high risk?" → get agentic answer

---

### DAY 5 — Polish, Testing, Demo Prep

**Owner: Full Team**

#### Block 1 (9AM–11AM): Bug Fixes + Error Handling

- Add loading spinners to all async components
- Add error toast for failed API calls
- Handle edge cases: unknown region, model not found, Pinecone timeout

#### Block 2 (11AM–1PM): Docker Compose (Optional but impressive)

```yaml
# docker-compose.yml
version: "3.8"
services:
  redis:
    image: redis:alpine
    ports: ["6379:6379"]

  ml-service:
    build: ./ml-service
    ports: ["8001:8001"]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001

  rag-service:
    build: ./rag-service
    ports: ["8003:8003"]
    env_file: ./rag-service/.env

  agent:
    build: ./agent
    ports: ["8002:8002"]
    env_file: ./agent/.env
    depends_on: [ml-service, rag-service]

  backend:
    build: ./backend
    ports: ["3001:3001"]
    depends_on: [redis, agent, ml-service]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

#### Block 3 (2PM–4PM): Demo Walkthrough Rehearsal

Rehearse this exact sequence:

1. Show Italy on risk map → RED (High risk)
2. Click Italy → ForecastChart shows rising trend
3. Open SHAP bar → "retail mobility is the top driver"
4. Move mobility slider down 20% → simulated line flattens
5. Open chat → "Why is Italy high risk and what should we do?"
6. Show the structured 4-part answer with policy recommendations

#### Block 4 (4PM–6PM): GitHub + README

```markdown
# README.md sections:

1. System Architecture diagram (ASCII or image)
2. How to run (docker-compose up OR manual steps)
3. Dataset sources + download instructions
4. Model performance metrics (RMSE, F1)
5. Demo GIF or screenshots
```

---

## 🔑 Critical Design Decisions

### Why LangGraph over LangChain Agents?

|                 | LangChain AgentExecutor  | LangGraph                                |
| --------------- | ------------------------ | ---------------------------------------- |
| Control flow    | Implicit, hard to debug  | Explicit graph — you see every edge      |
| Cycles          | Limited                  | First-class support                      |
| State           | No built-in shared state | TypedDict state passed through all nodes |
| Debugging       | print() or langsmith     | Step-by-step node inspection             |
| Hackathon value | "We used LangChain"      | "We designed a stateful reasoning graph" |

### Why Microservices over Monolith?

- ML service can be restarted (model reload) without affecting chat
- RAG ingestion is a one-time operation — separate process
- Judges can see each service independently — more impressive demo
- Redis caching works at the Node.js gateway level — clean separation

### Latency Bottlenecks (and fixes)

| Bottleneck       | Latency    | Fix                                               |
| ---------------- | ---------- | ------------------------------------------------- |
| Pinecone query   | ~300–500ms | Cache embedding + results in Redis for same query |
| GPT-4o synthesis | ~2–4s      | Stream the response token by token to frontend    |
| XGBoost predict  | ~10–50ms   | Negligible — no fix needed                        |
| Agent full cycle | ~5–8s      | Show typing indicator in ChatUI                   |

### Redis Improving UX

- Second request for same region returns in <10ms (vs 500ms+ cold)
- Prevents hammering Pinecone (paid service with rate limits)
- Map loads instantly for already-viewed regions

---

## ✅ Quick-Start Checklist (First 2 Hours)

```
□ Clone repo, create virtualenv
□ pip install all ML dependencies
□ Run: python -c "import xgboost; print(xgboost.__version__)"
□ Download JHU data (test with pd.read_csv)
□ Run feature_engineering.py → check features.csv has no all-NaN columns
□ Run train.py → check models/*.pkl files exist
□ Start FastAPI: uvicorn app.main:app --port 8001 --reload
□ curl http://localhost:8001/predict with Italy → get JSON
□ You now have a working ML backend. Everything else builds on this.
```
