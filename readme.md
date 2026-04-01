# Techsta Regional Epidemic Intelligence Platform

Techsta is a full-stack epidemic intelligence system with four public backend-facing capabilities:

- Forecasting via `POST /forecast`
- Intervention simulation via `POST /simulate`
- Risk assessment via `POST /risk`
- Conversational analysis via `POST /query`

This README is the primary developer guide for what is implemented, how to run the stack, how schemas are organized, and how to verify model and agent provenance through logs.

## What Is Implemented

### 1) API-preserving architecture

- Existing routes are preserved:
  - Backend gateway: `/forecast`, `/simulate`, `/risk`, `/query`
  - ML service: `/forecast`, `/simulate`, `/risk`
- Frontend calls backend only; backend proxies quantitative routes to ML and runs agent orchestration in-process for `/query`.

### 2) Artifact-first ML runtime (XGBoost)

- `ml-service` prioritizes notebook-exported XGBoost artifacts from `ml-service/data/models`.
- If artifact inference is unavailable for a request path, runtime uses fallback/template-safe behavior to keep contracts stable.
- Forecast payload supports both legacy trajectory and model-spec-aligned fields (dual mode).

### 3) Structured `/query` orchestration

- Backend invokes agent graph (planner -> verifier -> tool -> llm synthesis).
- Tool payloads are normalized into chart-friendly `structured_data` for frontend.
- Query responses include intent/tool/fallback fields and source references.

### 4) Observability and provenance logs

- INFO logs: concise request/response summaries and provenance markers.
- DEBUG logs: full input/output JSON payload visibility across gateway, transport, ml-service, and agent tools.
- Provenance logs explicitly indicate whether artifact-backed paths or fallback/LLM-oriented paths were used.

## Repository Layout

- `frontend/` Next.js app (dashboard + chat UI)
- `backend/` FastAPI gateway + in-process agent runner
- `ml-service/` FastAPI epidemic analytics service
- `rag-service/` retrieval API
- `agent/` LangGraph planner/tool modules
- `Epidemic_Spread_Prediction/` notebooks, model spec, and artifact export source

## Schema Ownership (Canonical Files)

### Backend request/response contracts

- `backend/app/schemas.py`
  - `ForecastRequest`
  - `SimulateRequest`
  - `RiskRequest`
  - `QueryRequest`
  - `QueryResponse`

### ML service contracts

- `ml-service/app/schemas.py`
  - `ForecastRequest`
  - `ForecastResponse`
  - `ForecastModelFeatures`
  - `SimulateRequest` / `SimulateResponse`
  - `RiskRequest` / `RiskResponse`

### Frontend type contracts

- `frontend/src/types/api.ts`

### Model I/O reference

- `Epidemic_Spread_Prediction/MODEL_API_SPEC.md`

## Startup

Use separate terminals from workspace root `C:\Users\akash\iit_bhu\techsta`.

### 1) Backend (port 8000)

```powershell
Set-Location "C:\Users\akash\iit_bhu\techsta\backend"
& "C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2) ML service (port 8001)

```powershell
Set-Location "C:\Users\akash\iit_bhu\techsta\ml-service"
& "C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 3) RAG service (port 8003)

```powershell
Set-Location "C:\Users\akash\iit_bhu\techsta\rag-service"
& "C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload
```

### 4) Frontend (port 3000)

```powershell
Set-Location "C:\Users\akash\iit_bhu\techsta\frontend"
npm run dev
```

## Environment and Logging Controls

### Backend

- `BACKEND_LOG_LEVEL` (`INFO` or `DEBUG`)
- `ML_URL` (default `http://localhost:8001`)
- `RAG_URL` (if used by backend route/tool flow)

### ML service

- `ML_SERVICE_LOG_LEVEL` (`INFO` or `DEBUG`)
- `EPIDEMIC_MODEL_ARTIFACT_DIR` (artifact directory override)
- `EPIDEMIC_ADAPTER_METADATA_PATH` (metadata override)
- `EPIDEMIC_STRICT_ARTIFACT_MODE` (`true` to fail fast when artifacts missing)

### Agent/tool environment

- `ML_URL`
- `RAG_URL`

## Health Checks

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8003/docs -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing
```

## How to Verify JSON I/O Visibility

Set log levels to `DEBUG`, then call endpoints.

Expected DEBUG tags include:

- Gateway router payloads:
  - `[GW-FORECAST][REQ_PAYLOAD]`, `[GW-FORECAST][RESP_PAYLOAD]`
  - `[GW-SIMULATE][REQ_PAYLOAD]`, `[GW-SIMULATE][RESP_PAYLOAD]`
  - `[GW-RISK][REQ_PAYLOAD]`, `[GW-RISK][RESP_PAYLOAD]`
  - `[QUERY][REQ_PAYLOAD]`, `[QUERY][RESP_PAYLOAD]`
- Transport payloads:
  - `[HTTP][REQ_PAYLOAD]`, `[HTTP][RESP_PAYLOAD]`
- ML service payloads:
  - `[ML-FORECAST][REQ_PAYLOAD]`, `[ML-FORECAST][RESP_PAYLOAD]`
  - `[ML-SIMULATE][REQ_PAYLOAD]`, `[ML-SIMULATE][RESP_PAYLOAD]`
  - `[ML-RISK][REQ_PAYLOAD]`, `[ML-RISK][RESP_PAYLOAD]`
- Agent/tool payloads:
  - `[AGENT_TOOL][FORECAST|SIMULATE|RISK|RAG][REQ_PAYLOAD|RESP_PAYLOAD]`

## How to Verify Provenance (Artifact vs Fallback vs LLM Path)

### ML provenance tags

- Adapter/runtime provenance:
  - `[EPI_PROVENANCE][INIT]`
  - `[EPI_PROVENANCE][FORECAST]`
  - `[EPI_PROVENANCE][SIMULATE]`
  - `[EPI_PROVENANCE][RISK]`
- Route-level source markers:
  - Forecast: `[ML-FORECAST][RESP] ... source=artifact artifact_used=true`
  - Forecast fallback: `[ML-FORECAST][RESP_FALLBACK] ... source=template artifact_used=false`
  - Similar for simulate and risk.

### Query/agent provenance tags

- Agent planner/tool/llm trace:
  - `[AGENT_PROVENANCE][PLANNER|VERIFIER|TOOL|LLM]`
- Backend query classification:
  - `[QUERY_PROVENANCE] ... query_path=llm_only|ml_tool|rag_only|mixed ...`
- Query response summary line includes path/source context from `run_agent`.

## Test Commands

From workspace root:

```powershell
Set-Location "C:\Users\akash\iit_bhu\techsta\ml-service"; python -m pytest -q
Set-Location "C:\Users\akash\iit_bhu\techsta\backend"; python -m pytest -q
Set-Location "C:\Users\akash\iit_bhu\techsta\frontend"; npm run test -- --run
Set-Location "C:\Users\akash\iit_bhu\techsta\frontend"; npm run build
```

## Quick Smoke Calls

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/forecast" -ContentType "application/json" -Body '{"region_id":"USA","horizon_days":3}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/simulate" -ContentType "application/json" -Body '{"region_id":"USA","intervention":{"mobility_reduction":0.2,"vaccination_increase":0.1}}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/risk" -ContentType "application/json" -Body '{"region_id":"USA"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/query" -ContentType "application/json" -Body '{"query":"Forecast for USA next 3 days","session_id":"dev-smoke"}'
```

## Notes for Developers

- Keep public route names and response contracts stable.
- Prefer adding observability through logs instead of schema changes when debugging provenance.
- If artifact loading fails, check interpreter/package alignment (`xgboost` availability) and artifact files in `ml-service/data/models`.
