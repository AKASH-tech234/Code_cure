import requests
import os
import logging

logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


def risk_tool(region: str) -> dict:
    """
    Calls ML service /risk endpoint.
    Returns unified risk assessment.
    """
    try:
        res = requests.post(
            f"{ML_URL}/risk",
            json={"region_id": region},
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error("[RISK_TOOL] Error: %s", str(e))
        raise
