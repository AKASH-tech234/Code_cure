"""
Unified error handling middleware.
Catches all exceptions and returns structured error envelope.
"""

import logging
import time
from fastapi import Request
from fastapi.responses import JSONResponse
import httpx

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    logger.info("[GATEWAY][REQ] method=%s path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[GATEWAY][RESP] method=%s path=%s status=%s latency_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response
    except httpx.TimeoutException:
        logger.error("[GATEWAY] Downstream service timeout for %s", request.url.path)
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "code": "SERVICE_TIMEOUT",
                    "message": "Downstream service did not respond in time",
                    "details": f"Request to {request.url.path} timed out"
                }
            }
        )
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.error("[GATEWAY] Downstream error %d for %s", status, request.url.path)
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": "DOWNSTREAM_ERROR",
                    "message": str(detail),
                    "details": f"HTTP {status} from downstream service"
                }
            }
        )
    except httpx.ConnectError:
        logger.error("[GATEWAY] Cannot connect to downstream service for %s", request.url.path)
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Downstream service is not available",
                    "details": "Connection refused"
                }
            }
        )
    except Exception as e:
        logger.exception("[GATEWAY] Unexpected error")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": str(e)
                }
            }
        )
