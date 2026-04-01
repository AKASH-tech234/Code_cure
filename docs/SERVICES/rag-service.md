# RAG Service

## Role

Retrieval service for external context used by agent responses.

## Routes

- `POST /retrieve`
- `POST /ingest`
- `GET /docs`

## Behavior

- Uses embedding-based retrieval.
- Uses Pinecone when configured.
- Keeps local fallback retrieval behavior for resilience.
