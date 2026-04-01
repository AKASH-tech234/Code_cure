# ML Service

## Role

Provides epidemic analytics endpoints used by backend and agent tools.

## Routes

- `POST /forecast`
- `POST /simulate`
- `POST /risk`
- `GET /health`

## Current Runtime Strategy

- USA runtime path enabled.
- Existing template fallback preserved for compatibility.
- Public request/response schema remains unchanged.
