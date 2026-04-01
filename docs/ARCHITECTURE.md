# Architecture

## High-Level Flow

1. Frontend (Next.js) sends requests to backend gateway.
2. Backend routes task-specific calls:
   - `/forecast`, `/simulate`, `/risk` -> ML service
   - `/query` -> in-process agent graph
3. Agent can call:
   - ML service tools for quantitative outputs
   - RAG service for context retrieval
4. Backend returns normalized payloads used by frontend charts and UI cards.

## Services and Ports

- Frontend: `http://127.0.0.1:3000`
- Backend Gateway: `http://127.0.0.1:8000`
- ML Service: `http://127.0.0.1:8001`
- RAG Service: `http://127.0.0.1:8003`

## Core Endpoints

### Backend

- `POST /forecast`
- `POST /simulate`
- `POST /risk`
- `POST /query`
- `GET /health`

### ML Service

- `POST /forecast`
- `POST /simulate`
- `POST /risk`
- `GET /health`

### RAG Service

- `POST /retrieve`
- `POST /ingest`
- `GET /docs`

## Contract Stability Rule

Public route names and payload shapes are intentionally stable so frontend and agent integrations remain intact while internal ML implementation evolves.
