from fastapi import APIRouter, HTTPException
from app.schemas import ForecastRequest, ForecastResponse
from app.data.region_templates import (
    get_region, compute_risk_score, risk_level_from_score, get_as_of_date
)
from app.services import epidemic_runtime

router = APIRouter()


@router.post("", response_model=ForecastResponse)
def forecast(body: ForecastRequest):
    """
    Forecast endpoint — predicts case trajectory for a region.

    Uses region template data to generate a plausible forecast curve
    based on base_cases * (1 + growth_rate)^day compounding.
    """
    region_id = body.region_id.upper()

    if epidemic_runtime.supports_region(region_id):
        try:
            epi = epidemic_runtime.forecast(region_id=region_id, horizon_days=body.horizon_days)
            return ForecastResponse(
                region_id=epi.region_id,
                predicted_cases=epi.predicted_cases,
                growth_rate=epi.growth_rate,
                risk_score=epi.risk_score,
                risk_level=epi.risk_level,
                horizon_days=epi.horizon_days,
                as_of_date=epi.as_of_date,
            )
        except Exception:
            # Keep service resilient: runtime failure should not break existing template behavior.
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

    return ForecastResponse(
        region_id=region_id,
        predicted_cases=predicted_cases,
        growth_rate=round(growth, 4),
        risk_score=risk_score,
        risk_level=risk_level_from_score(risk_score),
        horizon_days=body.horizon_days,
        as_of_date=get_as_of_date()
    )
