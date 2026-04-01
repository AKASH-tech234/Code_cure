# Frontend

## Role

Next.js UI for dashboard and chat workflows.

## Views

- Dashboard: forecast, risk, simulation controls
- Chat: multi-turn query interface with structured outputs

## API Dependency

Frontend talks only to backend gateway (`http://127.0.0.1:8000`).
It does not call ML or RAG services directly.

## Start

```powershell
cd C:\Users\akash\iit_bhu\techsta\frontend
npm run dev
```
