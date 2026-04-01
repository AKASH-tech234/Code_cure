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
        logger.info(
            "[AGENT_TOOL][SIMULATE][REQ] region_id=%s mobility_reduction=%.3f vaccination_increase=%.3f",
            region,
            payload["intervention"]["mobility_reduction"],
            payload["intervention"]["vaccination_increase"],
        )
        logger.debug("[AGENT_TOOL][SIMULATE][REQ_PAYLOAD] payload=%s", payload)
        res = requests.post(
            f"{ML_URL}/simulate",
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        parsed = res.json()
        logger.info("[AGENT_TOOL][SIMULATE][RESP] status=%s", res.status_code)
        logger.debug("[AGENT_TOOL][SIMULATE][RESP_PAYLOAD] payload=%s", parsed)
        return parsed
    except Exception as e:
        logger.error("[SIMULATE_TOOL] Error: %s", str(e))
        raise