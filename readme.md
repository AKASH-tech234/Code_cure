# Techsta Regional Epidemic Intelligence Platform

Techsta is a full-stack epidemic intelligence system that combines forecasting,
risk analysis, intervention simulation, and AI-assisted reasoning.

It includes:

- Frontend dashboard and chat interface
- Backend gateway with in-process agent orchestration
- ML service for forecast/simulate/risk endpoints
- RAG service for evidence retrieval
- ML research workspace in `Epidemic_Spread_Prediction`

## Key Features

- Regional 7-day forecast responses via `POST /forecast`
- Intervention simulation via `POST /simulate`
- Risk scoring and drivers via `POST /risk`
- Multi-turn natural language analysis via `POST /query`
- Structured chart-ready payloads for frontend rendering

## Startup Commands

Use separate terminals.

### Terminal 1 - Backend (8000)

```powershell
cd C:\Users\akash\iit_bhu\techsta\backend
& C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2 - ML Service (8001)

```powershell
cd C:\Users\akash\iit_bhu\techsta\ml-service
& C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Terminal 3 - RAG Service (8003)

```powershell
cd C:\Users\akash\iit_bhu\techsta\rag-service
& C:\Users\akash\iit_bhu\techsta\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload
```

### Terminal 4 - Frontend (3000)

```powershell
cd C:\Users\akash\iit_bhu\techsta\frontend
npm run dev
```

## Health Checks

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8003/docs -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing
```

## How It Works Internally

1. Frontend sends requests to backend gateway only.
2. Backend forwards quantitative calls to ML service.
3. Backend executes agent graph in-process for `POST /query`.
4. Agent tools call ML and RAG services as needed.
5. Backend returns normalized response payloads used by frontend components.

## Repository Layout

- `frontend/` Next.js UI
- `backend/` FastAPI gateway and session manager
- `ml-service/` FastAPI epidemic analytics API
- `rag-service/` Retrieval and ingestion API
- `agent/` LangGraph planner/tooling modules
- `Epidemic_Spread_Prediction/` ML model research notebooks and specs
- `docs/` Centralized project documentation

## Documentation

- Main docs index: [docs/README.md](docs/README.md)
- Quickstart: [docs/QUICKSTART.md](docs/QUICKSTART.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Service docs: [docs/SERVICES](docs/SERVICES)
