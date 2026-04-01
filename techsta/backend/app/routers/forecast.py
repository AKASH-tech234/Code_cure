import os
from fastapi import APIRouter
from ..schemas import ForecastRequest
from ..services.http_client import call_service

router = APIRouter()

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


@router.post("")
async def forecast(body: ForecastRequest):
    """Proxy /forecast to ML service."""
    result = await call_service(
        url=f"{ML_URL}/forecast",
        payload=body.model_dump()
    )
    return result
