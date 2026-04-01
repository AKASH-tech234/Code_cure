import logging
import time

from fastapi import APIRouter, HTTPException
from app.schemas import ForecastRequest, ForecastResponse
from app.data.region_templates import (
    get_region, compute_risk_score, risk_level_from_score, get_as_of_date
)
from app.services import epidemic_runtime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ForecastResponse)
def forecast(body: ForecastRequest):
    """
    Forecast endpoint — predicts case trajectory for a region.

    Uses region template data to generate a plausible forecast curve
    based on base_cases * (1 + growth_rate)^day compounding.
    """
    started_at = time.perf_counter()
    region_id = body.region_id.upper()
    request_payload = body.model_dump()

    logger.info(
        "[ML-FORECAST][REQ] region_id=%s horizon_days=%s has_features=%s has_prev_roll7=%s",
        region_id,
        body.horizon_days,
        body.features is not None,
        body.prev_roll7 is not None,
    )
    logger.debug("[ML-FORECAST][REQ_PAYLOAD] payload=%s", request_payload)

    if epidemic_runtime.supports_region(region_id):
        try:
            epi = epidemic_runtime.forecast(
                region_id=region_id,
                horizon_days=body.horizon_days,
                features=body.features.model_dump() if body.features else None,
                prev_roll7=body.prev_roll7,
                prediction_date=body.prediction_date,
                country=body.country,
            )
            response = ForecastResponse(
                region_id=epi.region_id,
                predicted_cases=epi.predicted_cases,
                growth_rate=epi.growth_rate,
                risk_score=epi.risk_score,
                risk_level=epi.risk_level,
                horizon_days=epi.horizon_days,
                as_of_date=epi.as_of_date,
                prediction_date=epi.prediction_date,
                country=epi.country,
                point_forecast=epi.point_forecast,
                prediction_interval_80pct=epi.prediction_interval_80pct,
                model_metadata=epi.model_metadata,
            )

            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "[ML-FORECAST][RESP] region_id=%s risk_level=%s risk_score=%.3f latency_ms=%.2f",
                response.region_id,
                response.risk_level,
                response.risk_score,
                latency_ms,
            )
            logger.debug("[ML-FORECAST][RESP_PAYLOAD] payload=%s", response.model_dump())
            return response
        except Exception:
            # Keep service resilient: runtime failure should not break existing template behavior.
            logger.exception("[ML-FORECAST] adapter path failed, using template fallback")
            pass

    region = get_region(region_id)
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{body.region_id}' not found. Use ISO alpha-3 codes (e.g., ITA, IND, USA)."
        )

    base = region["base_cases"]
    growth = region["growth_rate"]

    # Generate forecast: compounding growth per day
    predicted_cases = []
    current = base
    for day in range(body.horizon_days):
        daily_growth = growth / 7  # weekly growth → daily
        current = int(current * (1 + daily_growth))
        predicted_cases.append(current)

    # Compute risk
    risk_score = compute_risk_score(
        growth_rate=growth,
        mobility=region["mobility_index"],
        vaccination_rate=region["vaccination_rate"],
        hospital_pressure=region["hospital_pressure"]
    )

    response = ForecastResponse(
        region_id=region_id,
        predicted_cases=predicted_cases,
        growth_rate=round(growth, 4),
        risk_score=risk_score,
        risk_level=risk_level_from_score(risk_score),
        horizon_days=body.horizon_days,
        as_of_date=get_as_of_date()
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[ML-FORECAST][RESP_FALLBACK] region_id=%s risk_level=%s risk_score=%.3f latency_ms=%.2f",
        response.region_id,
        response.risk_level,
        response.risk_score,
        latency_ms,
    )
    logger.debug("[ML-FORECAST][RESP_FALLBACK_PAYLOAD] payload=%s", response.model_dump())
    return response
