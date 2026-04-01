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
        payload = {"region_id": region}
        logger.info("[AGENT_TOOL][RISK][REQ] region_id=%s", region)
        logger.debug("[AGENT_TOOL][RISK][REQ_PAYLOAD] payload=%s", payload)
        res = requests.post(
            f"{ML_URL}/risk",
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        parsed = res.json()
        logger.info("[AGENT_TOOL][RISK][RESP] status=%s", res.status_code)
        logger.debug("[AGENT_TOOL][RISK][RESP_PAYLOAD] payload=%s", parsed)
        return parsed
    except Exception as e:
        logger.error("[RISK_TOOL] Error: %s", str(e))
        raise
