# Implementation Notes

## Current Direction

- Keep existing service topology.
- Keep all public route contracts unchanged.
- Integrate epidemic model behavior inside `ml-service` incrementally.
- Preserve non-US compatibility via existing fallback behavior until later refinement.

## Safety Boundaries

Do not change these without explicit migration:

- Backend external route names
- Frontend API payload assumptions
- Agent tool endpoint contracts

## Recent Updates

- Added USA runtime path in `ml-service` with fallback.
- Added startup runtime initialization in `ml-service`.
- Added integration tests for runtime path and compatibility.

## Next Engineering Steps

1. Replace deterministic runtime internals with artifact-backed inference.
2. Add metadata/artifact loader with explicit versioning.
3. Extend validation and smoke tests.
4. Continue docs and operational hardening.
