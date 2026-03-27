import requests
import os
import logging

logger = logging.getLogger(__name__)

ML_URL = os.getenv("ML_URL", "http://localhost:8001")


def simulate_tool(region: str, intervention: dict) -> dict:
    """
    Calls ML service /simulate endpoint.
    No hardcoded fallbacks.
    """
    try:
        payload = {
            "region_id": region,
            "intervention": {
                "mobility_reduction": float(intervention.get("mobility_reduction") or 0),
                "vaccination_increase": float(intervention.get("vaccination_increase") or 0),
            }
        }
        res = requests.post(
            f"{ML_URL}/simulate",
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error("[SIMULATE_TOOL] Error: %s", str(e))
        raise