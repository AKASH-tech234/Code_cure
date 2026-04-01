# Quickstart

## Prerequisites

- Python 3.12 recommended
- Node.js 18+ and npm
- Windows PowerShell

## One-Time Setup

From repo root:

```powershell
cd C:\Users\akash\iit_bhu\techsta

# Python deps (shared root .venv)
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r ml-service\requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r rag-service\requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r agent\requirements.txt

# Frontend deps
cd frontend
npm install
```

## Start All Services

Open 4 terminals from repo root.

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

## Important Runtime Note

There is no separate agent server to start. Agent logic runs in-process inside backend for `POST /query`.
