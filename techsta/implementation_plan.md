# 🧠 Regional Epidemic Intelligence System — Implementation Plan & Deep System Specification

> **CODECURE AI Hackathon | Track C**
> Based on analysis of: [readme.md](file:///c:/Users/akash/iit_bhu/techsta/readme.md), existing [agent/](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py#27-54) and `rag-service/` code

---

## 📋 TABLE OF CONTENTS

1. [Current Repository Analysis](#1-current-repository-analysis)
2. [Architecture Mapping: Current → Final](#2-architecture-mapping-current--final)
3. [Detailed Service Breakdown](#3-detailed-service-breakdown)
4. [Full API I/O Specification](#4-full-api-io-specification)
5. [Step-by-Step Implementation Plan (4 Phases)](#5-step-by-step-implementation-plan)
6. [Microservice Communication Flow](#6-microservice-communication-flow)
7. [Agent Architecture Deep Dive & Upgrade](#7-agent-architecture-deep-dive--upgrade)
8. [RAG Pipeline Deep Dive & Upgrade](#8-rag-pipeline-deep-dive--upgrade)
9. [Memory Design](#9-memory-design)
10. [Frontend Strategy](#10-frontend-strategy)
11. [Error & Fallback Design](#11-error--fallback-design)
12. [Full User Journey Trace](#12-full-user-journey-trace)
13. [Folder Structure Plan](#13-folder-structure-plan)
14. [Risk Areas & Mitigation](#14-risk-areas--mitigation)
15. [Testing Strategy](#15-testing-strategy)
16. [Deployment Strategy](#16-deployment-strategy)

---

## 1. CURRENT REPOSITORY ANALYSIS

### What Exists

| Component | Path | Status | Issues |
|-----------|------|--------|--------|
| **Agent Service** | [agent/](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py#27-54) | Partially built | Uses `input()`/`print()` (CLI), no FastAPI wrapper, empty [main.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/main.py)/[schemas.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/schemas.py)/[registry.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/registry.py)/[edges.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/edges.py) |
| **RAG Service** | `rag-service/` | Working | Pinecone + local fallback, SentenceTransformer, 5 PDF docs ingested |
| **ML Service** | — | **Does not exist** | No `ml-service/` directory |
| **Backend Gateway** | — | **Does not exist** | No `backend/` directory |
| **Frontend** | — | **Does not exist** | No `frontend/` directory |

### Agent — Detailed Current State

| File | Lines | Key Content |
|------|-------|-------------|
| [state.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/state.py) | 20 | [AgentState](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/state.py#4-21) TypedDict with: query, intent, tool, reasoning, region, intervention, missing_fields, context, answer, sources, memory, followup_question |
| [nodes.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py) | 166 | 5 nodes: [planner_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#12-78), [followup_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) (⚠️ `input()`), [tool_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#100-122), [rag_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#138-150), [llm_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#150-167) |
| [build_graph.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/build_graph.py) | 38 | Graph: planner → conditional → {followup↩planner, tool→llm, direct→llm} |
| [client.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/llm/client.py) | 34 | Uses **Groq** (`openai/gpt-oss-120b`), temperature=0.2 |
| [forecast_tool.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/forecast_tool.py) | 30 | Calls ML_URL `/forecast`, has hardcoded mock fallback |
| [simulate_tool.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/simulate_tool.py) | 32 | Calls ML_URL `/simulate`, has hardcoded mock fallback |
| [rag_tool.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/rag_tool.py) | 42 | Calls RAG_URL `/retrieve`, graceful error handling |
| [agent.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py) | 53 | Simple RAG→LLM pipeline (bypasses LangGraph entirely) |

### RAG Service — Detailed Current State

| File | Lines | Key Content |
|------|-------|-------------|
| [main.py](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/main.py) | 22 | FastAPI app, startup loads resources |
| [retriever.py](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/retrieval/retriever.py) | 162 | Dual retrieval: Pinecone first → local fallback, `all-MiniLM-L6-v2` embeddings |
| [ingest_docs.py](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/ingestion/ingest_docs.py) | 143 | Ingests txt + PDF docs, 500-char chunks w/ 100 overlap, upserts to Pinecone |
| [schemas.py](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/schemas.py) | 12 | [RetrieveRequest(query, top_k)](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/schemas.py#4-7), [RetrieveResponse(context, sources)](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/schemas.py#8-11) |

### Critical Issues Found

> [!CAUTION]
> 1. **[followup_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) uses `print()` and `input()`** — blocks forever in server context
> 2. **[agent/app/main.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/main.py) is empty** — no FastAPI wrapper exists
> 3. **Tools have hardcoded mock fallbacks** — violates "no hardcoded data" rule
> 4. **No structured JSON output enforcement** — planner uses raw LLM text→JSON parse with bare `except`
> 5. **[agent.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py) bypasses LangGraph** — simple RAG→LLM, not the graph pipeline
> 6. **No session/memory management** — memory dict is ephemeral per request

---

## 2. ARCHITECTURE MAPPING: CURRENT → FINAL

### Target Architecture (from User Requirements)

```
┌─────────────────────────────────────────────────────┐
│               FRONTEND (Next.js)                     │
│  Chat │ Explanation Panel │ Region Selector           │
│  Sliders (mobility, vaccination) │ Dashboard Charts   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP only
┌──────────────────────▼──────────────────────────────┐
│      BACKEND GATEWAY (FastAPI — merged w/ Agent)     │
│  POST /forecast → ML Service                         │
│  POST /simulate → ML Service                         │
│  POST /risk     → ML Service                         │
│  POST /query    → Agent (LangGraph) → ML/RAG         │
│  Session Manager (in-memory, TTL)                     │
└──────┬──────────────────────┬───────────────────────┘
       │                      │
┌──────▼──────────┐   ┌──────▼──────────┐
│  ML SERVICE     │   │  RAG SERVICE     │
│  FastAPI        │   │  FastAPI          │
│  /forecast      │   │  /retrieve        │
│  /simulate      │   │  Pinecone +       │
│  /risk          │   │  SentenceTransf.  │
└─────────────────┘   └──────────────────┘
```

### Mapping Table

| README Architecture | Final Architecture | Change |
|---|---|---|
| React frontend | **Next.js** App Router | **Replace** — full rewrite |
| Node.js Express backend | **FastAPI** (Python) | **Replace** — merged with Agent |
| ML Service (FastAPI, port 8001) | ML Service (FastAPI, port 8001) | **New** — create from scratch |
| Agent Service (FastAPI, port 8002) | **Merged into Gateway** (port 8000) | **Refactor** — no separate service |
| RAG Service (FastAPI, port 8003) | RAG Service (FastAPI, port 8003) | **Upgrade** — existing works |
| Redis caching | **In-memory dict with TTL** | **Simplify** — no Redis dependency |

> [!IMPORTANT]
> The final architecture merges the **Backend Gateway + Agent Service** into a single FastAPI application (port 8000). The agent graph runs in-process. This eliminates one network hop and simplifies deployment.

---

## 3. DETAILED SERVICE BREAKDOWN

### 3.1 ML Service (Port 8001)

**Role:** Stateless computation engine — forecast, simulate, risk assessment

| Aspect | Detail |
|--------|--------|
| Framework | FastAPI |
| Endpoints | `/forecast`, `/simulate`, `/risk` |
| Data | Uses template/stub data (no real model training required) |
| Input format | ISO alpha-3 region codes (ITA, IND, USA) |
| Output format | Deterministic JSON schemas |
| Does NOT | Reason, explain, converse, store state |

### 3.2 Backend Gateway + Agent (Port 8000)

**Role:** Single entry point for all frontend requests. Routes `/forecast`, `/simulate`, `/risk` to ML. Routes `/query` through LangGraph agent.

| Aspect | Detail |
|--------|--------|
| Framework | FastAPI |
| Routes | `/forecast`, `/simulate`, `/risk`, `/query` |
| Session Manager | In-memory dict, TTL=30min, thread-safe |
| Agent | LangGraph graph compiled in-process |
| Memory | Injected into agent state per request, persisted after response |

### 3.3 RAG Service (Port 8003)

**Role:** Pure document retrieval. No reasoning.

| Aspect | Detail |
|--------|--------|
| Framework | FastAPI (already exists) |
| Endpoint | `/retrieve` |
| Vector store | Pinecone (`iitb` index) |
| Embedding | `all-MiniLM-L6-v2` (384-dim) |
| Fallback | Local cosine similarity over [docs.txt](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/data/docs.txt) |
| Returns | `{context: string, sources: string[]}` |

### 3.4 Frontend (Port 3000)

**Role:** Next.js App Router — dashboard, simulation, chat

| Aspect | Detail |
|--------|--------|
| Framework | Next.js (App Router) |
| State | `session_id` + `selected_region` + slider values |
| Talks to | ONLY Backend Gateway (port 8000) |
| Never calls | ML or RAG directly |

---

## 4. FULL API I/O SPECIFICATION

### 4.1 POST /forecast

**Input Schema:**
```json
{
  "region_id": "ITA",        // ISO alpha-3, required
  "horizon_days": 7          // int, optional, default 7
}
```

**Internal Processing:**
1. Gateway validates `region_id` format (3 uppercase letters)
2. Gateway forwards to ML Service `POST http://ml:8001/forecast`
3. ML loads latest feature row for region
4. ML runs recursive 1-step XGBoost prediction for `horizon_days` steps
5. ML classifies risk level from current features
6. ML computes growth rate from lag features
7. Returns structured JSON

**Output Schema:**
```json
{
  "region_id": "ITA",
  "predicted_cases": [14200, 15100, 16300, 16800, 17100, 17400, 17600],
  "growth_rate": 0.08,
  "risk_score": 0.78,
  "risk_level": "High",
  "horizon_days": 7,
  "as_of_date": "2024-01-15"
}
```

**Dependencies:** Johns Hopkins time-series, OWID vaccination/stringency data

---

### 4.2 POST /simulate

**Input Schema:**
```json
{
  "region_id": "ITA",
  "intervention": {
    "mobility_reduction": 0.20,       // [0–1], required
    "vaccination_increase": 0.10      // [0–1], required
  }
}
```

**Internal Processing:**
1. Gateway validates intervention values are in [0, 1] range
2. Gateway forwards to ML Service `POST http://ml:8001/simulate`
3. ML loads latest feature row for region
4. ML predicts baseline (no intervention)
5. ML creates modified feature row: `mobility -= reduction`, `vaccination += increase`
6. ML predicts simulated trajectory
7. Computes delta = baseline - simulated
8. Returns comparison

**Output Schema:**
```json
{
  "region_id": "ITA",
  "baseline_cases": [16800, 17100, 17400, 17800, 18200, 18600, 19000],
  "simulated_cases": [14100, 13200, 12800, 12500, 12200, 12000, 11800],
  "delta_cases": 22400,
  "impact_summary": "20% mobility reduction + 10% vaccination increase could avert ~22,400 cases over 7 days"
}
```

---

### 4.3 POST /risk

**Input Schema:**
```json
{
  "region_id": "ITA"
}
```

**Internal Processing:**
1. Gateway forwards to ML Service `POST http://ml:8001/risk`
2. ML computes unified risk: `risk = f(predicted_growth, mobility, vaccination, hospital_pressure)`
3. Thresholds: score > 0.7 = High, 0.4–0.7 = Medium, < 0.4 = Low
4. Identifies top 3 risk drivers with weights

**Output Schema:**
```json
{
  "region_id": "ITA",
  "risk_level": "High",
  "risk_score": 0.78,
  "drivers": [
    {"factor": "predicted_growth_rate", "value": 0.08, "weight": 0.35},
    {"factor": "mobility_index", "value": 0.23, "weight": 0.25},
    {"factor": "vaccination_gap", "value": 0.38, "weight": 0.22},
    {"factor": "hospital_pressure", "value": 0.15, "weight": 0.18}
  ]
}
```

> [!IMPORTANT]
> Risk MUST be unified: `risk_score = w1*growth + w2*mobility + w3*(1-vaccination) + w4*hospital_pressure`. Not a separate model — a formula-based composite.

---

### 4.4 POST /query

**Input Schema:**
```json
{
  "query": "Why is Italy high risk and what should we do?",
  "session_id": "abc-123",               // optional, auto-generated if missing
  "context": {                            // optional override
    "region_id": "ITA",
    "intervention": null
  }
}
```

**Internal Flow:**
```
1. Gateway: look up session memory by session_id
2. Gateway: inject memory + query into AgentState
3. Agent Graph: planner_node → extracts intent, region, tool choice, missing_fields
4. Agent Graph: IF missing_fields → return followup (no tools called)
5. Agent Graph: tool_node → calls ML or RAG via HTTP
6. Agent Graph: llm_node → synthesizes explanation from tool results
7. Gateway: persist updated memory (region, intent, resolved fields)
8. Gateway: return structured response
```

**Output Schema:**
```json
{
  "session_id": "abc-123",
  "answer": "Based on current epidemiological data...",
  "intent": "explain",
  "tool_used": "forecast",
  "reasoning": "User wants to understand Italy's risk drivers",
  "data": {                              // raw tool output, for frontend charts
    "forecast": { ... },
    "risk": { ... }
  },
  "followup": {                          // null if no missing fields
    "question": "Which region would you like to analyze?",
    "missing_fields": ["region_id"]
  } 
}
```

**Every `/query` response ALWAYS has this exact schema.** [followup](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) is `null` when all fields are resolved.

---

## 5. STEP-BY-STEP IMPLEMENTATION PLAN

### Phase 1: Schemas + ML Service Stubs (Day 1)

| Step | Task | Files | Done Criteria |
|------|------|-------|---------------|
| 1.1 | Create `ml-service/` directory structure | `ml-service/app/{main.py, routers/, schemas.py}` | Directory exists |
| 1.2 | Define Pydantic schemas for all 3 endpoints | `ml-service/app/schemas.py` | `ForecastRequest/Response`, `SimulateRequest/Response`, `RiskRequest/Response` |
| 1.3 | Implement `/forecast` stub | `ml-service/app/routers/forecast.py` | Returns valid structured JSON with plausible template values based on region |
| 1.4 | Implement `/simulate` stub | `ml-service/app/routers/simulate.py` | Returns baseline vs simulated arrays, delta computed from intervention |
| 1.5 | Implement `/risk` stub | `ml-service/app/routers/risk.py` | Returns risk_level, risk_score, drivers array |
| 1.6 | Wire FastAPI app + test all 3 endpoints | `ml-service/app/main.py` | `uvicorn` starts, curl returns valid JSON for all endpoints |
| 1.7 | Create [requirements.txt](file:///c:/Users/akash/iit_bhu/techsta/agent/requirements.txt) | `ml-service/requirements.txt` | `fastapi`, `uvicorn`, `pydantic`, `python-dotenv` |

> [!NOTE]
> ML stubs should return **region-aware template data** (not random). Use a dictionary mapping region codes to plausible base values. E.g., ITA → 15000 cases baseline, IND → 85000, USA → 45000. Apply intervention math to produce realistic simulated outputs.

---

### Phase 2: Gateway + Session Manager (Day 2)

| Step | Task | Files | Done Criteria |
|------|------|-------|---------------|
| 2.1 | Create `backend/` directory as FastAPI gateway | `backend/app/{main.py, routers/, session.py, schemas.py}` | Directory exists |
| 2.2 | Implement session manager | `backend/app/session.py` | In-memory dict with TTL (30min), thread-safe (`threading.Lock`), auto-cleanup |
| 2.3 | Implement `/forecast` route (proxy to ML) | `backend/app/routers/forecast.py` | Forwards to ML, returns response |
| 2.4 | Implement `/simulate` route (proxy to ML) | `backend/app/routers/simulate.py` | Forwards to ML, returns response |
| 2.5 | Implement `/risk` route (proxy to ML) | `backend/app/routers/risk.py` | Forwards to ML, returns response |
| 2.6 | Implement unified error envelope | `backend/app/middleware/error_handler.py` | All errors return `{error: {code, message, details}}` |
| 2.7 | Add timeout + retry for downstream calls | `backend/app/services/http_client.py` | `httpx.AsyncClient` with 10s timeout, 2 retries |
| 2.8 | Add CORS middleware | `backend/app/main.py` | Frontend on port 3000 can call port 8000 |

---

### Phase 3: Agent Refactor + /query Route (Day 3)

| Step | Task | Files | Done Criteria |
|------|------|-------|---------------|
| 3.1 | Refactor [AgentState](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/state.py#4-21) — add session fields | [agent/app/graph/state.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/state.py) | Add `session_id`, `memory`, remove CLI-specific fields |
| 3.2 | **Remove [followup_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99)** — replace with [followup](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) return | [agent/app/graph/nodes.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py) | No `input()`, no `print()` anywhere |
| 3.3 | Refactor [planner_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#12-78) — strict JSON output | [agent/app/graph/nodes.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py) | LLM prompt enforces JSON schema, parse with validation |
| 3.4 | Refactor [tool_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#100-122) — remove hardcoded mocks | [agent/app/tools/forecast_tool.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/forecast_tool.py), [simulate_tool.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/simulate_tool.py) | Tools only return data from ML service, raise on ML failure |
| 3.5 | Add `risk_tool.py` | `agent/app/tools/risk_tool.py` | Calls ML `/risk` endpoint |
| 3.6 | Implement [registry.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/registry.py) | [agent/app/tools/registry.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/tools/registry.py) | `TOOL_REGISTRY = {name: fn}` |
| 3.7 | Rebuild graph — remove followup loop | [agent/app/graph/build_graph.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/build_graph.py) | planner → tool → llm (linear), followup via return value |
| 3.8 | Implement `/query` route in gateway | `backend/app/routers/query.py` | Injects memory, calls graph, persists memory, returns structured JSON |
| 3.9 | Implement runner layer | `backend/app/services/agent_runner.py` | [run_agent(query, session_id)](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py#27-54) → injects memory → calls graph → returns result |

---

### Phase 4: Frontend Integration (Day 4-5)

| Step | Task | Files | Done Criteria |
|------|------|-------|---------------|
| 4.1 | Create Next.js app | `frontend/` | `npx create-next-app` with App Router |
| 4.2 | API client module | `frontend/src/lib/api.ts` | Axios instance pointing to `http://localhost:8000` |
| 4.3 | Region selector component | `frontend/src/components/RegionSelector.tsx` | Dropdown with ISO alpha-3 codes |
| 4.4 | Dashboard page — forecast chart | `frontend/src/app/page.tsx` | Calls `/forecast` on region select, renders line chart |
| 4.5 | Simulation sliders component | `frontend/src/components/SimulationSliders.tsx` | mobility [0–1] + vaccination [0–1] sliders |
| 4.6 | Simulation overlay on chart | `frontend/src/components/ForecastChart.tsx` | Baseline + simulated lines |
| 4.7 | Risk badge component | `frontend/src/components/RiskBadge.tsx` | Color-coded pill (red/yellow/green) |
| 4.8 | Chat panel component | `frontend/src/components/ChatPanel.tsx` | Input → POST /query → display answer |
| 4.9 | Explanation panel | `frontend/src/components/ExplanationPanel.tsx` | Shows intent, tool used, reasoning |
| 4.10 | Polish: loading states, error handling, animations | All components | Spinners, error toasts, smooth transitions |

---

## 6. MICROSERVICE COMMUNICATION FLOW

### Scenario A — Forecast (Dashboard Load)

```
User selects "ITA" in region dropdown
  │
  ▼
Frontend: POST http://localhost:8000/forecast
  body: { "region_id": "ITA", "horizon_days": 7 }
  │
  ▼
Gateway (port 8000):
  1. Validate region_id format
  2. Forward: POST http://localhost:8001/forecast { same body }
  │
  ▼
ML Service (port 8001):
  1. Look up region "ITA" in template data
  2. Generate 7-day forecast array
  3. Compute growth_rate, risk_score
  4. Return JSON
  │
  ▼
Gateway:
  1. Receive ML response
  2. Wrap in standard envelope
  3. Return to frontend
  │
  ▼
Frontend:
  1. Parse predicted_cases array
  2. Render line chart
  3. Show risk badge (color from risk_level)
```

### Scenario B — Simulation (Slider Change)

```
User moves mobility slider to 0.3, vaccination to 0.15
  │
  ▼
Frontend: POST http://localhost:8000/simulate
  body: { "region_id": "ITA", "intervention": { "mobility_reduction": 0.3, "vaccination_increase": 0.15 } }
  │
  ▼
Gateway → ML Service:
  1. Load baseline for ITA
  2. Apply: mobility_index -= 0.3, vaccination += 0.15
  3. Predict simulated trajectory
  4. Compute delta_cases = sum(baseline) - sum(simulated)
  │
  ▼
Frontend:
  1. Overlay simulated_cases line (dashed) on existing forecast chart
  2. Show delta_cases and impact_summary
```

### Scenario C — Chat Query (Agent Path)

```
User types: "Why is Italy high risk and what should we do?"
  │
  ▼
Frontend: POST http://localhost:8000/query
  body: { "query": "Why is Italy high risk...", "session_id": "abc-123" }
  │
  ▼
Gateway:
  1. Load session memory for "abc-123" (or create new)
  2. Build AgentState: { query, memory, region: memory.region_id or null }
  3. Call: graph.invoke(state)
  │
  ▼
Agent Graph (in-process):
  ┌─ planner_node ─────────────────────────────────┐
  │ LLM extracts: intent="risk_explain",            │
  │   region="ITA", tool="forecast+risk",           │
  │   missing_fields=[]                              │
  └──────────────────┬─────────────────────────────┘
                     ▼
  ┌─ tool_node ────────────────────────────────────┐
  │ Calls ML /forecast: gets predicted_cases,       │
  │   growth_rate, risk_score                       │
  │ Calls ML /risk: gets risk_level, drivers        │
  │ Calls RAG /retrieve: gets guidelines context    │
  └──────────────────┬─────────────────────────────┘
                     ▼
  ┌─ llm_node ─────────────────────────────────────┐
  │ Synthesizes: "Italy is trending High because... │
  │   retail mobility +23%... WHO recommends..."    │
  └──────────────────┬─────────────────────────────┘
                     ▼
Gateway:
  1. Persist updated memory (region="ITA", last_intent="risk_explain")
  2. Return: { answer, intent, tool_used, reasoning, data, followup: null }
  │
  ▼
Frontend:
  1. Display answer in chat panel
  2. Show intent + tool + reasoning in explanation panel
  3. If followup != null → show follow-up prompt
```

---

## 7. AGENT ARCHITECTURE DEEP DIVE & UPGRADE

### Current Agent System

**Nodes:**
- [planner_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#12-78) — LLM extracts intent/tool/region/intervention/missing_fields from query + memory
- [followup_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) — ⚠️ Uses `print()` + `input()` to ask user for missing fields
- [tool_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#100-122) — Dispatches to forecast/simulate/rag tools based on `state["tool"]`
- [rag_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#138-150) — Separate RAG retrieval (redundant with tool_node's rag path)
- [llm_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#150-167) — Synthesizes final answer from context

**Graph Flow:**
```
planner → conditional:
  ├─ missing_fields? → followup → planner (loop)
  ├─ tool="none"? → llm
  └─ else → tool → llm
```

### Current Limitations

1. **[followup_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) blocks forever** — `input()` in server = deadlock
2. **No structured output validation** — bare `except` on JSON parse; LLM can return any format
3. **Hardcoded mock fallbacks** in tools — violates data integrity rule
4. **No schema enforcement** on tool outputs — tools return raw dicts
5. **[rag_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#138-150) and [tool_node](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#100-122) both handle RAG** — duplicated logic
6. **No session_id / memory persistence** — memory is ephemeral
7. **[agent.py](file:///c:/Users/akash/iit_bhu/techsta/agent/app/agent.py) bypasses graph entirely** — simple RAG→LLM, unused by graph

### Proposed Upgrade

#### 7.1 Remove followup_node, Replace with Return Value

Instead of looping with `input()`, the graph returns a [followup](file:///c:/Users/akash/iit_bhu/techsta/agent/app/graph/nodes.py#85-99) object in the response:

```
IF missing_fields not empty:
  → skip tool_node and llm_node
  → return { followup: { question, missing_fields }, answer: null }
  → frontend displays follow-up question
  → user submits next query
  → gateway calls graph again WITH previous memory (region now filled)
```

**Graph becomes strictly linear per request:** planner → (tool → llm) OR (return followup)

#### 7.2 Strict JSON Planner Output

Planner prompt must enforce exact schema:

```json
{
  "intent": "forecast|simulate|risk|general_info",
  "tool": "forecast|simulate|risk|rag|none",
  "region": "ITA|null",
  "intervention": {"mobility_reduction": 0.2, "vaccination_increase": 0.1},
  "missing_fields": ["region_id"],
  "reasoning": "string",
  "followup_question": "Which country do you want to analyze?"
}
```

Parse with `json.loads()` + Pydantic validation. On parse failure, retry once with a repair prompt.

#### 7.3 Tool Contract Enforcement

Every tool function signature:
- **Input:** receives exactly the fields it needs (region, intervention, query)
- **Output:** returns a Pydantic-validated dict or raises `ToolExecutionError`
- **No fallback mocks** — if ML is down, tool raises error → gateway returns error envelope

#### 7.4 Deterministic Routing

```python
INTENT_TO_TOOLS = {
    "forecast":     ["forecast"],
    "simulate":     ["simulate"],
    "risk":         ["risk"],
    "risk_explain": ["forecast", "risk", "rag"],
    "general_info": ["rag"],
}
```

No LLM needed for routing — deterministic map from intent to tool list.

#### 7.5 Unified Graph (New)

```
planner → check_missing:
  ├─ missing? → return followup (END)
  └─ not missing → tool_executor → llm_synthesizer (END)
```

`tool_executor` iterates through the tool list (forecast, risk, rag) and collects all results before passing to synthesizer.

---

## 8. RAG PIPELINE DEEP DIVE & UPGRADE

### Current RAG

- **Documents:** 5 PDFs + 1 [docs.txt](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/data/docs.txt) file
- **Embedding:** `all-MiniLM-L6-v2` (384-dim)
- **Chunking:** 500-char chunks, 100-char overlap (character-based, not token-based)
- **Retrieval:** Pinecone query → local fallback
- **Output:** concatenated text chunks + source labels

### Current Limitations

1. **Small knowledge base** — only 5 PDFs
2. **Character-based chunking** — may split mid-sentence
3. **No ranking/filtering** — returns top-k by cosine, no relevance threshold
4. **No context compression** — returns full chunks even if mostly irrelevant
5. **No metadata filtering** — can't filter by source type (WHO/CDC/research)

### Upgrade Strategy

| Improvement | Current | Target |
|---|---|---|
| Chunking | 500 char, 100 overlap | `RecursiveCharacterTextSplitter` with 400 token, 50 token overlap, paragraph-aware |
| Metadata | `{text, source}` | `{text, source, source_type, doc_name, chunk_index}` |
| Retrieval | Top-k only | Top-k + score threshold (> 0.5) + optional source_type filter |
| Context compression | None | Truncate to 2000 chars total (prevents LLM context overflow) |
| Re-ranking | None | Optional: re-rank top-10 → pick top-4 by cross-encoder |

> [!NOTE]
> For the hackathon, upgrading chunking and adding metadata filtering is sufficient. Re-ranking is a stretch goal.

### Re-ingestion Required After Upgrade

If chunking changes, must re-ingest all documents:
```
1. Delete Pinecone index content
2. Update ingest_docs.py with new chunking
3. Re-run ingestion
4. Verify via /retrieve test query
```

---

## 9. MEMORY DESIGN

### Per-Session Memory Fields

```json
{
  "session_id": "abc-123",
  "created_at": "2024-01-15T10:00:00Z",
  "last_accessed": "2024-01-15T10:05:00Z",
  "ttl_seconds": 1800,
  
  "region_id": "ITA",
  "intervention": {
    "mobility_reduction": 0.20,
    "vaccination_increase": 0.10
  },
  "last_intent": "risk_explain",
  "previous_queries": [
    "What is the forecast for Italy?",
    "Why is Italy high risk?"
  ],
  "resolved_fields": ["region_id", "intervention"]
}
```

### What NOT to Store

- Full raw API responses (too large)
- Embeddings (computed on-the-fly)
- Full conversation history (only last 5 queries)

### Memory Lifecycle

1. **Creation:** First `/query` request without session_id → generate UUID → create memory entry
2. **Update:** Each `/query` request → update `last_accessed`, merge new fields (region, intervention, intent)
3. **TTL Expiration:** Background task every 60s removes sessions where `now - last_accessed > ttl_seconds`

### Memory Usage in Agent

- **Injected into planner:** planner sees `memory.region_id` so user doesn't need to repeat "Italy"
- **Fills missing fields:** if planner needs region but memory has it → no followup needed
- **Improves multi-turn:** "Now reduce mobility by 30%" → planner uses `memory.region_id = ITA`

---

## 10. FRONTEND STRATEGY

### State Management

```
Local state per component:
- session_id: string (generated on first /query call, stored in sessionStorage)
- selected_region: string (ISO alpha-3, from RegionSelector)
- mobility_value: number [0–1] (from slider)
- vaccination_value: number [0–1] (from slider)
- chat_messages: array [{role, content}]
```

### UI Logic — When to Call Which API

| User Action | API Called | UI Update |
|---|---|---|
| Select region in dropdown | `POST /forecast` + `POST /risk` | Render forecast chart + risk badge |
| Move mobility/vaccination slider | `POST /simulate` (debounced 300ms) | Overlay simulated line on chart |
| Type message in chat | `POST /query` | Append answer to chat, show explanation panel |
| Click "analyze" from chat follow-up | `POST /query` (with resolved fields) | Same as above |

### Rendering

- **Forecast chart:** Line chart (Recharts/Chart.js) — X=days, Y=cases, two lines: actual (solid) + predicted (dashed)
- **Simulation overlay:** Third line (dotted, different color) for `simulated_cases`
- **Risk badge:** Pill component — red="High", yellow="Medium", green="Low"
- **Explanation panel:** Accordion/sidebar showing `intent`, `tool_used`, `reasoning` from `/query` response

---

## 11. ERROR & FALLBACK DESIGN

### Unified Error Envelope

Every endpoint returns errors in this format:
```json
{
  "error": {
    "code": "ML_UNAVAILABLE",
    "message": "ML service is not responding",
    "details": "Connection refused at http://localhost:8001"
  }
}
```

### Fallback Strategies

| Failure | Fallback | User Sees |
|---|---|---|
| ML Service down | Gateway returns error with code `ML_UNAVAILABLE` | "Prediction service temporarily unavailable. Dashboard data may be stale." |
| RAG Service down | Agent returns answer without RAG context, adds disclaimer | Chat answer with "(Note: guideline context unavailable)" |
| Agent graph error | Gateway catches exception, returns generic error | "Unable to process your question. Please try again." |
| LLM (Groq) down | [generate_answer](file:///c:/Users/akash/iit_bhu/techsta/agent/app/llm/client.py#17-35) returns error string | "AI reasoning temporarily unavailable" |
| Invalid region_id | ML returns 404 | "Region 'XYZ' not found. Please use ISO alpha-3 codes." |

### Key Principle: Dashboard Still Works Without Agent/RAG

`/forecast`, `/simulate`, `/risk` routes go directly to ML service. If Agent or RAG are down, the dashboard and simulation still function. Only `/query` (chat) is affected.

---

## 12. FULL USER JOURNEY TRACE

**Journey: User selects Italy → sees forecast → adjusts mobility → sees simulation → asks question → agent explains**

| Step | User Action | System Flow | User Sees |
|------|-------------|-------------|-----------|
| 1 | Selects "ITA" in region dropdown | Frontend: `POST /forecast {region_id: "ITA", horizon_days: 7}` → Gateway → ML → Response | Line chart: 7-day case forecast trending upward |
| 2 | (automatic) | Frontend: `POST /risk {region_id: "ITA"}` → Gateway → ML → Response | Red "High" risk badge, drivers table |
| 3 | Moves mobility slider to 0.3 | Frontend: `POST /simulate {region_id: "ITA", intervention: {mobility_reduction: 0.3, vaccination_increase: 0}}` (debounced) | Dotted overlay line: simulated cases drop below baseline |
| 4 | Moves vaccination slider to 0.15 | Frontend: `POST /simulate` (updated intervention) | Overlay updates: further case reduction, shows "~22,400 cases averted" |
| 5 | Types: "Why is Italy high risk and what should we do?" | Frontend: `POST /query {query: "...", session_id: "abc-123"}` → Gateway → Agent Graph → planner(intent=risk_explain) → tool(forecast+risk+rag) → synthesizer | Chat: 4-part answer with situation summary, risk drivers, WHO guidelines, recommendations |
| 6 | (automatic) | Explanation panel reads `intent: "risk_explain"`, `tool_used: "forecast+risk+rag"`, `reasoning` | Sidebar: shows agent reasoning trace |
| 7 | Asks follow-up: "What if we increase vaccination to 20%?" | Frontend: `POST /query` → Agent uses `memory.region_id=ITA`, understands context | Chat: simulation comparison, updated recommendations |

---

## 13. FOLDER STRUCTURE PLAN

```
techsta/
├── frontend/                          # [NEW] Next.js App Router
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Dashboard
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── RegionSelector.tsx
│   │   │   ├── ForecastChart.tsx
│   │   │   ├── SimulationSliders.tsx
│   │   │   ├── RiskBadge.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   └── ExplanationPanel.tsx
│   │   └── lib/
│   │       └── api.ts                 # Axios client
│   ├── package.json
│   └── .env.local
│
├── backend/                           # [NEW] FastAPI Gateway (merged w/ Agent)
│   ├── app/
│   │   ├── main.py                    # FastAPI app, CORS, route mounting
│   │   ├── routers/
│   │   │   ├── forecast.py            # POST /forecast → proxy to ML
│   │   │   ├── simulate.py            # POST /simulate → proxy to ML
│   │   │   ├── risk.py                # POST /risk → proxy to ML
│   │   │   └── query.py               # POST /query → Agent graph
│   │   ├── services/
│   │   │   ├── http_client.py         # httpx client with timeout/retry
│   │   │   └── agent_runner.py        # Injects memory, calls graph, persists
│   │   ├── session.py                 # In-memory session store with TTL
│   │   ├── schemas.py                 # Gateway-level Pydantic models
│   │   └── middleware/
│   │       └── error_handler.py       # Unified error envelope
│   ├── requirements.txt
│   └── .env
│
├── ml-service/                        # [NEW] FastAPI ML stubs
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── forecast.py
│   │   │   ├── simulate.py
│   │   │   └── risk.py
│   │   ├── schemas.py                 # Pydantic models for all I/O
│   │   └── data/
│   │       └── region_templates.py    # Template data per region
│   ├── requirements.txt
│   └── .env
│
├── agent/                             # [REFACTOR] LangGraph Agent
│   ├── app/
│   │   ├── graph/
│   │   │   ├── state.py               # [MODIFY] Updated AgentState
│   │   │   ├── nodes.py               # [MODIFY] Remove followup_node, refactor
│   │   │   ├── edges.py               # [MODIFY] Add routing logic
│   │   │   └── build_graph.py         # [MODIFY] New linear graph
│   │   ├── tools/
│   │   │   ├── forecast_tool.py       # [MODIFY] Remove mock fallback
│   │   │   ├── simulate_tool.py       # [MODIFY] Remove mock fallback
│   │   │   ├── risk_tool.py           # [NEW] Calls ML /risk
│   │   │   ├── rag_tool.py            # [KEEP] Already correct
│   │   │   └── registry.py            # [MODIFY] Populate registry
│   │   ├── llm/
│   │   │   └── client.py              # [KEEP] Groq client
│   │   ├── schemas.py                 # [MODIFY] Add Pydantic models
│   │   ├── agent.py                   # [DELETE] Replaced by graph
│   │   └── main.py                    # [DELETE] Not needed (merged into gateway)
│   ├── requirements.txt
│   └── .env
│
├── rag-service/                       # [UPGRADE] Existing RAG
│   ├── app/
│   │   ├── main.py                    # [KEEP]
│   │   ├── routers/
│   │   │   └── retrieve.py            # [KEEP]
│   │   ├── retrieval/
│   │   │   └── retriever.py           # [UPGRADE] Add metadata filtering
│   │   ├── ingestion/
│   │   │   └── ingest_docs.py         # [UPGRADE] Better chunking
│   │   ├── schemas.py                 # [KEEP]
│   │   └── data/
│   │       ├── docs.txt
│   │       └── pdfs/
│   ├── requirements.txt
│   └── .env
│
├── readme.md
└── .gitignore
```

---

## 14. RISK AREAS & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM JSON parse failure in planner | High | Agent returns empty/broken response | Pydantic validation + retry-once with repair prompt + fallback default intent |
| Groq API rate limiting / downtime | Medium | Chat unusable | Add 3-retry with exponential backoff; consider Gemini fallback (key exists in .env) |
| Pinecone cold start latency (~2s) | Medium | First RAG query slow | Warm-up on startup via [load_resources()](file:///c:/Users/akash/iit_bhu/techsta/rag-service/app/retrieval/retriever.py#30-65) (already implemented) |
| Frontend ↔ Backend CORS issues | High | Requests blocked | Explicit `CORSMiddleware` with `origins=["http://localhost:3000"]` |
| Session memory leak | Low | Server OOM over time | TTL cleanup task every 60s; max 1000 sessions |
| Tool timeout (ML or RAG) | Medium | Agent hangs | 5s timeout on all HTTP calls in tools; raise `ToolExecutionError` |
| ISO alpha-3 validation | Medium | Invalid region passed to ML | Validate against known set in gateway before forwarding |

---

## 15. TESTING STRATEGY

### Unit Tests

| Test | Command | What it Validates |
|------|---------|-------------------|
| ML schemas | `cd ml-service && python -m pytest tests/test_schemas.py` | Pydantic models accept valid input, reject invalid |
| Session manager | `cd backend && python -m pytest tests/test_session.py` | Create, read, update, TTL expiry |
| Planner JSON parsing | `cd agent && python -m pytest tests/test_planner.py` | LLM output → parsed intent + fields |

### Integration Tests

| Test | Command | What it Validates |
|------|---------|-------------------|
| ML endpoints | `cd ml-service && uvicorn app.main:app --port 8001 &` then `curl` all 3 endpoints | JSON schema compliance |
| Gateway → ML proxy | Start ML + Gateway, `curl http://localhost:8000/forecast` | Response passes through correctly |
| Agent graph end-to-end | Start all services, `curl http://localhost:8000/query` | Full pipeline: planner→tool→llm returns structured response |
| RAG retrieval | `curl http://localhost:8003/retrieve -d '{"query":"outbreak control","top_k":3}'` | Returns non-empty context |

### Multi-Turn Tests

| Scenario | Steps | Expected |
|----------|-------|----------|
| Missing region | `/query {"query": "forecast cases"}` → should return followup asking for region | `followup.missing_fields = ["region_id"]` |
| Region from memory | Step 1: `/query {"query": "forecast for Italy"}` → Step 2: `/query {"query": "now simulate"}` | Step 2 uses `memory.region_id = "ITA"` |
| Session TTL | Create session → wait 31 min → query again | Should create new session, not find old one |

### Manual Verification

1. **Start all services** → verify no startup errors
2. **Open frontend** → select ITA → verify chart renders
3. **Move sliders** → verify simulation overlay updates
4. **Type chat query** → verify structured answer appears
5. **Check explanation panel** → verify intent/tool/reasoning displayed

---

## 16. DEPLOYMENT STRATEGY

### Local Development

```bash
# Terminal 1: RAG Service
cd rag-service && uvicorn app.main:app --port 8003 --reload

# Terminal 2: ML Service  
cd ml-service && uvicorn app.main:app --port 8001 --reload

# Terminal 3: Backend Gateway
cd backend && uvicorn app.main:app --port 8000 --reload

# Terminal 4: Frontend
cd frontend && npm run dev  # port 3000
```

### Cloud Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | `https://epidemic-intel.vercel.app` |
| Backend Gateway | Render (Web Service) | `https://epidemic-api.onrender.com` |
| ML Service | Render (Web Service) | `https://epidemic-ml.onrender.com` |
| RAG Service | Render (Web Service) | `https://epidemic-rag.onrender.com` |

**Environment Variables for Cloud:**
- Frontend: `NEXT_PUBLIC_API_URL=https://epidemic-api.onrender.com`
- Gateway: `ML_URL=https://epidemic-ml.onrender.com`, `RAG_URL=https://epidemic-rag.onrender.com`
- ML: No external dependencies
- RAG: `PINECONE_API_KEY`, `PINECONE_INDEX`

---

## VERIFICATION PLAN

### How to Verify This Plan is Complete

1. ✅ Every endpoint has INPUT → PROCESS → OUTPUT defined
2. ✅ Every service has clear responsibility boundaries
3. ✅ Data flow diagrams show exact request/response chain
4. ✅ Current codebase issues are identified with fixes
5. ✅ Phase-wise steps are ordered by dependency
6. ✅ No `input()`, `print()`, or CLI interaction anywhere in final design
7. ✅ All responses are structured JSON with fixed schemas
8. ✅ `region_id` uses ISO alpha-3 everywhere
9. ✅ Risk is unified formula, not separate model
10. ✅ Frontend only talks to gateway
