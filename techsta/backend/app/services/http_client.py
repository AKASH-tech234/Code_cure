"""
HTTP client for downstream service calls.
Uses httpx with timeout and retry logic.
"""

import httpx
import logging
from typing import Optional

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
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(
                "[HTTP] Timeout calling %s (attempt %d/%d)",
                url, attempt + 1, retries + 1
            )
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors
            if e.response.status_code < 500:
                raise
            last_error = e
            logger.warning(
                "[HTTP] Server error %d from %s (attempt %d/%d)",
                e.response.status_code, url, attempt + 1, retries + 1
            )
        except httpx.HTTPError as e:
            last_error = e
            logger.warning(
                "[HTTP] Error calling %s: %s (attempt %d/%d)",
                url, str(e), attempt + 1, retries + 1
            )

    raise last_error
