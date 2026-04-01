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

## Epidemic_Spread_Prediction Mapping (Priority Source)

The service keeps the same public routes (`/forecast`, `/simulate`, `/risk`) and
the same request/response schemas used by backend, frontend, and agent tools.

Model-priority behavior is implemented internally through an adapter that applies
Epidemic_Spread_Prediction signal logic first, then falls back safely.

### Forecast Mapping

- Source spec context: `country`, lag/policy features, and point + interval output
  (`predicted_roll7_cases`, `lower_q10`, `upper_q90`)
- Public contract preserved:
  - Request remains `{ region_id, horizon_days }`
  - Response remains `{ region_id, predicted_cases[], growth_rate, risk_score, risk_level, horizon_days, as_of_date }`
- Internal mapping:
  - Adapter derives lag-style and policy signals from region state
  - Adapter rolls forward for `horizon_days` and emits `predicted_cases[]`
  - Risk outputs are projected to existing `risk_score`/`risk_level`

### Risk Mapping

- Source spec context: model-driven feature influence (e.g., reproduction/policy signals)
- Public contract preserved:
  - Request remains `{ region_id }`
  - Response remains `{ region_id, risk_level, risk_score, drivers[] }`
- Internal mapping:
  - Adapter computes model-priority risk state
  - Adapter returns exactly 4 normalized drivers aligned with existing UI expectations

### Simulation Mapping

- Source spec focuses on prediction; simulation remains an ml-service orchestration layer.
- Public contract preserved:
  - Request remains `{ region_id, intervention: { mobility_reduction, vaccination_increase } }`
  - Response remains `{ region_id, baseline_cases[], simulated_cases[], delta_cases, impact_summary }`
- Internal mapping:
  - Adapter applies intervention deltas to policy/signal state and performs comparative rollout.

### Compatibility Guarantees

- No route changes.
- No required field changes.
- No status-code contract changes (`200`, `404`, `422` preserved).
- No files removed from `Epidemic_Spread_Prediction/`.
