# Techsta Documentation

This folder is the single source of truth for project documentation.

## Contents

- [Quickstart](QUICKSTART.md)
- [Architecture](ARCHITECTURE.md)
- [Implementation Notes](IMPLEMENTATION.md)
- Service docs:
  - [Backend](SERVICES/backend.md)
  - [ML Service](SERVICES/ml-service.md)
  - [RAG Service](SERVICES/rag-service.md)
  - [Agent](SERVICES/agent.md)
  - [Frontend](SERVICES/frontend.md)
- ML reference:
  - [Epidemic Model README](../Epidemic_Spread_Prediction/README.md)
  - [Model API Spec](../Epidemic_Spread_Prediction/MODEL_API_SPEC.md)

## Current Stack

- Frontend: Next.js on port 3000
- Backend Gateway: FastAPI on port 8000
- ML Service: FastAPI on port 8001
- RAG Service: FastAPI on port 8003

Use [Quickstart](QUICKSTART.md) to run all services.
