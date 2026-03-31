import requests
import os
import logging

logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


def forecast_tool(region: str) -> dict:
    """
    Calls ML service /forecast endpoint.
    No hardcoded fallbacks.
    """
    try:
        res = requests.post(
            f"{ML_URL}/forecast",
            json={"region_id": region, "horizon_days": 7},
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error("[FORECAST_TOOL] Error: %s", str(e))
        raise