import logging
import time

from fastapi import APIRouter, HTTPException
from app.schemas import SimulateRequest, SimulateResponse
from app.data.region_templates import get_region
from app.services import epidemic_runtime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=SimulateResponse)
def simulate(body: SimulateRequest):
    """
    Simulation endpoint — compares baseline vs intervention trajectory.

    Applies intervention effects:
    - mobility_reduction: each 0.1 reduces daily growth by ~15%
    - vaccination_increase: each 0.1 reduces daily growth by ~10%
    """
    started_at = time.perf_counter()
    region_id = body.region_id.upper()
    request_payload = body.model_dump()

    logger.info(
        "[ML-SIMULATE][REQ] region_id=%s mobility_reduction=%.3f vaccination_increase=%.3f",
        region_id,
        body.intervention.mobility_reduction,
        body.intervention.vaccination_increase,
    )
    logger.debug("[ML-SIMULATE][REQ_PAYLOAD] payload=%s", request_payload)

    if epidemic_runtime.supports_region(region_id):
        try:
            epi = epidemic_runtime.simulate(
                region_id=region_id,
                mobility_reduction=body.intervention.mobility_reduction,
                vaccination_increase=body.intervention.vaccination_increase,
            )
            response = SimulateResponse(
                region_id=epi.region_id,
                baseline_cases=epi.baseline_cases,
                simulated_cases=epi.simulated_cases,
                delta_cases=epi.delta_cases,
                impact_summary=epi.impact_summary,
            )
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "[ML-SIMULATE][RESP] region_id=%s delta_cases=%s latency_ms=%.2f",
                response.region_id,
                response.delta_cases,
                latency_ms,
            )
            logger.debug("[ML-SIMULATE][RESP_PAYLOAD] payload=%s", response.model_dump())
            return response
        except Exception:
            # Keep service resilient: runtime failure should not break existing template behavior.
            logger.exception("[ML-SIMULATE] adapter path failed, using template fallback")
            pass

    region = get_region(region_id)
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{body.region_id}' not found. Use ISO alpha-3 codes."
        )

    base = region["base_cases"]
    growth = region["growth_rate"]
    horizon = 7  # fixed simulation horizon

    # Baseline trajectory (no intervention)
    baseline_cases = []
    current = base
    daily_growth = growth / 7
    for _ in range(horizon):
        current = int(current * (1 + daily_growth))
        baseline_cases.append(current)

    # Simulated trajectory (with intervention)
    mobility_effect = body.intervention.mobility_reduction * 0.15  # each 0.1 → 1.5% growth reduction
    vaccination_effect = body.intervention.vaccination_increase * 0.10  # each 0.1 → 1% growth reduction
    adjusted_growth = max(growth - mobility_effect - vaccination_effect, -0.05)  # allow slight decline
    adjusted_daily = adjusted_growth / 7

    simulated_cases = []
    current = base
    for _ in range(horizon):
        current = int(current * (1 + adjusted_daily))
        simulated_cases.append(current)

    delta = sum(baseline_cases) - sum(simulated_cases)

    # Build impact summary
    parts = []
    if body.intervention.mobility_reduction > 0:
        parts.append(f"{int(body.intervention.mobility_reduction * 100)}% mobility reduction")
    if body.intervention.vaccination_increase > 0:
        parts.append(f"{int(body.intervention.vaccination_increase * 100)}% vaccination increase")
    intervention_desc = " + ".join(parts) if parts else "no intervention"

    impact_summary = (
        f"{intervention_desc} could avert ~{max(delta, 0):,} cases over {horizon} days"
    )

    response = SimulateResponse(
        region_id=region_id,
        baseline_cases=baseline_cases,
        simulated_cases=simulated_cases,
        delta_cases=max(delta, 0),
        impact_summary=impact_summary
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[ML-SIMULATE][RESP_FALLBACK] region_id=%s delta_cases=%s latency_ms=%.2f",
        response.region_id,
        response.delta_cases,
        latency_ms,
    )
    logger.debug("[ML-SIMULATE][RESP_FALLBACK_PAYLOAD] payload=%s", response.model_dump())
    return response
