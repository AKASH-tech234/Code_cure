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
        payload = {"region_id": region, "horizon_days": 7}
        logger.info("[AGENT_TOOL][FORECAST][REQ] region_id=%s", region)
        logger.debug("[AGENT_TOOL][FORECAST][REQ_PAYLOAD] payload=%s", payload)
        res = requests.post(
            f"{ML_URL}/forecast",
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        parsed = res.json()
        logger.info(
            "[AGENT_TOOL][FORECAST][RESP] status=%s source=%s",
            res.status_code,
            "artifact" if parsed.get("model_metadata") else "template-or-legacy",
        )
        logger.debug("[AGENT_TOOL][FORECAST][RESP_PAYLOAD] payload=%s", parsed)
        return parsed
    except Exception as e:
        logger.error("[FORECAST_TOOL] Error: %s", str(e))
        raise