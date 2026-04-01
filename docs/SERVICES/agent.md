# Agent Runtime

## Role

LangGraph-based reasoning pipeline used by backend `/query`.

## Important Note

No standalone agent server is required in normal operation.
Agent logic is executed inside backend process.

## Tooling

- Forecast tool -> ML service `/forecast`
- Simulate tool -> ML service `/simulate`
- Risk tool -> ML service `/risk`
- RAG tool -> RAG service `/retrieve`
