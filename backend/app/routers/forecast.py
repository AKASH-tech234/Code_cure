import os
import logging
import time
from fastapi import APIRouter
from ..schemas import ForecastRequest
from ..services.http_client import call_service

router = APIRouter()
logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


@router.post("")
async def forecast(body: ForecastRequest):
    """Proxy /forecast to ML service."""
    started_at = time.perf_counter()
    request_payload = body.model_dump(exclude_none=True)
    logger.info(
        "[GW-FORECAST][REQ] region_id=%s horizon_days=%s has_features=%s",
        body.region_id.upper(),
        body.horizon_days,
        body.features is not None,
    )
    logger.debug("[GW-FORECAST][REQ_PAYLOAD] payload=%s", request_payload)

    result = await call_service(
        url=f"{ML_URL}/forecast",
        payload=request_payload,
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "[GW-FORECAST][RESP] region_id=%s latency_ms=%.2f",
        body.region_id.upper(),
        latency_ms,
    )
    logger.debug("[GW-FORECAST][RESP_PAYLOAD] payload=%s", result)
    return result
