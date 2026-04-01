import os
import logging
import time
from fastapi import APIRouter
from ..schemas import SimulateRequest
from ..services.http_client import call_service

router = APIRouter()
logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


@router.post("")
async def simulate(body: SimulateRequest):
    """Proxy /simulate to ML service."""
    started_at = time.perf_counter()
    request_payload = body.model_dump(exclude_none=True)
    logger.info(
        "[GW-SIMULATE][REQ] region_id=%s mobility_reduction=%.3f vaccination_increase=%.3f",
        body.region_id.upper(),
        body.intervention.mobility_reduction,
        body.intervention.vaccination_increase,
    )
    logger.debug("[GW-SIMULATE][REQ_PAYLOAD] payload=%s", request_payload)

    result = await call_service(
        url=f"{ML_URL}/simulate",
        payload=request_payload,
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[GW-SIMULATE][RESP] region_id=%s delta_cases=%s latency_ms=%.2f",
        body.region_id.upper(),
        result.get("delta_cases"),
        latency_ms,
    )
    logger.debug("[GW-SIMULATE][RESP_PAYLOAD] payload=%s", result)
    return result
