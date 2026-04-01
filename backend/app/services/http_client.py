"""
HTTP client for downstream service calls.
Uses httpx with timeout and retry logic.
"""

import httpx
import logging
import time

logger = logging.getLogger(__name__)

# Default timeouts
DEFAULT_TIMEOUT = 10.0  # seconds
MAX_RETRIES = 2


async def call_service(
    url: str,
    payload: dict,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES
) -> dict:
    """
    Make a POST request to a downstream service.
    Returns parsed JSON response.
    Raises httpx.HTTPError on failure after retries.
    """
    last_error = None

    for attempt in range(retries + 1):
        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                parsed = response.json()
                latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "[HTTP][RESP] url=%s status=%s attempt=%s latency_ms=%.2f",
                    url,
                    response.status_code,
                    attempt + 1,
                    latency_ms,
                )
                logger.debug("[HTTP][REQ_PAYLOAD] url=%s payload=%s", url, payload)
                logger.debug("[HTTP][RESP_PAYLOAD] url=%s payload=%s", url, parsed)
                return parsed
        except httpx.TimeoutException as e:
            last_error = e
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "[HTTP] Timeout calling %s (attempt %d/%d, %.2f ms)",
                url, attempt + 1, retries + 1, latency_ms
            )
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors
            if e.response.status_code < 500:
                raise
            last_error = e
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "[HTTP] Server error %d from %s (attempt %d/%d, %.2f ms)",
                e.response.status_code, url, attempt + 1, retries + 1, latency_ms
            )
        except httpx.HTTPError as e:
            last_error = e
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "[HTTP] Error calling %s: %s (attempt %d/%d, %.2f ms)",
                url, str(e), attempt + 1, retries + 1, latency_ms
            )

    raise last_error
