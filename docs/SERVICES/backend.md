# Backend Service

## Role

FastAPI gateway that exposes the main API consumed by frontend.

## Main Routes

- `POST /forecast`
- `POST /simulate`
- `POST /risk`
- `POST /query`
- `GET /health`

## Internal Behavior

- Proxies forecast/simulate/risk to ML service.
- Runs agent graph in-process for `/query`.
- Maintains lightweight session memory for multi-turn chat.
- Normalizes structured chart payloads for frontend.
