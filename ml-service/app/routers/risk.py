from fastapi import APIRouter, HTTPException
from app.schemas import RiskRequest, RiskResponse, RiskDriver
from app.data.region_templates import (
    get_region, compute_risk_score, risk_level_from_score, RISK_WEIGHTS
)
from app.services import epidemic_runtime

router = APIRouter()


@router.post("", response_model=RiskResponse)
def risk(body: RiskRequest):
    """
    Risk assessment endpoint — unified risk computation.

    risk_score = w1*growth + w2*mobility + w3*(1-vaccination) + w4*hospital_pressure

    Returns risk level, score, and individual driver contributions.
    """
    region_id = body.region_id.upper()

    if epidemic_runtime.supports_region(region_id):
        try:
            epi = epidemic_runtime.risk(region_id=region_id)
            return RiskResponse(
                region_id=epi.region_id,
                risk_level=epi.risk_level,
                risk_score=epi.risk_score,
                drivers=[
                    RiskDriver(factor=d.factor, value=d.value, weight=d.weight)
                    for d in epi.drivers
                ],
            )
        except Exception:
            # Keep service resilient: runtime failure should not break existing template behavior.
            pass

    region = get_region(region_id)
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"Region '{body.region_id}' not found. Use ISO alpha-3 codes."
        )

    growth = region["growth_rate"]
    mobility = region["mobility_index"]
    vaccination = region["vaccination_rate"]
    hospital = region["hospital_pressure"]

    risk_score = compute_risk_score(growth, mobility, vaccination, hospital)
    risk_level = risk_level_from_score(risk_score)

    # Break down into individual driver contributions
    growth_normalized = min(growth / 0.15, 1.0)
    vaccination_gap = 1.0 - vaccination

    drivers = [
        RiskDriver(
            factor="predicted_growth_rate",
            value=round(growth_normalized, 3),
            weight=RISK_WEIGHTS["predicted_growth_rate"]
        ),
        RiskDriver(
            factor="mobility_index",
            value=round(mobility, 3),
            weight=RISK_WEIGHTS["mobility_index"]
        ),
        RiskDriver(
            factor="vaccination_gap",
            value=round(vaccination_gap, 3),
            weight=RISK_WEIGHTS["vaccination_gap"]
        ),
        RiskDriver(
            factor="hospital_pressure",
            value=round(hospital, 3),
            weight=RISK_WEIGHTS["hospital_pressure"]
        ),
    ]

    return RiskResponse(
        region_id=region_id,
        risk_level=risk_level,
        risk_score=risk_score,
        drivers=drivers
    )
