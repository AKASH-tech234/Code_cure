import os
import logging
import time
from fastapi import APIRouter
from ..schemas import RiskRequest
from ..services.http_client import call_service

router = APIRouter()
logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


@router.post("")
async def risk(body: RiskRequest):
    """Proxy /risk to ML service."""
    started_at = time.perf_counter()
    request_payload = body.model_dump(exclude_none=True)
    logger.info("[GW-RISK][REQ] region_id=%s", body.region_id.upper())
    logger.debug("[GW-RISK][REQ_PAYLOAD] payload=%s", request_payload)

    result = await call_service(
        url=f"{ML_URL}/risk",
        payload=request_payload,
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[GW-RISK][RESP] region_id=%s risk_level=%s risk_score=%s latency_ms=%.2f",
        body.region_id.upper(),
        result.get("risk_level"),
        result.get("risk_score"),
        latency_ms,
    )
    logger.debug("[GW-RISK][RESP_PAYLOAD] payload=%s", result)
    return result
