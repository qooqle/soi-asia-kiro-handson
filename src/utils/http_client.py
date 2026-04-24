"""
http_client.py
HTTP GET with exponential back-off retry for the Internet Adoption Analysis pipeline.
"""
from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_BACKOFF_DELAYS = [1, 2, 4]


class HTTPError(IOError):
    """Raised when a non-retriable HTTP error is encountered."""


def get_with_retry(
    url: str,
    params: dict | None = None,
    timeout: int = 30,
    max_attempts: int = 3,
) -> requests.Response:
    """GET with exponential back-off. Retries on 5xx and timeouts; not on 4xx."""
    params = params or {}
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)

            if 400 <= response.status_code < 500:
                logger.error("HTTP %d for %s — client error, not retrying.", response.status_code, url)
                raise HTTPError(f"HTTP {response.status_code} (client error) for URL: {url}")

            if response.status_code >= 500:
                logger.warning("HTTP %d for %s — attempt %d/%d.", response.status_code, url, attempt, max_attempts)
                last_exc = HTTPError(f"HTTP {response.status_code} (server error) for URL: {url}")
                if attempt < max_attempts:
                    time.sleep(_BACKOFF_DELAYS[min(attempt - 1, len(_BACKOFF_DELAYS) - 1)])
                continue

            return response

        except requests.exceptions.Timeout as exc:
            logger.warning("Timeout after %ds for %s — attempt %d/%d.", timeout, url, attempt, max_attempts)
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(_BACKOFF_DELAYS[min(attempt - 1, len(_BACKOFF_DELAYS) - 1)])

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Connection error for %s — attempt %d/%d: %s", url, attempt, max_attempts, exc)
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(_BACKOFF_DELAYS[min(attempt - 1, len(_BACKOFF_DELAYS) - 1)])

    logger.error("All %d attempts failed for %s.", max_attempts, url)
    raise last_exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    test_url = "https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.PCAP.KD"
    test_params = {"date": "2020:2020", "format": "json", "per_page": "1"}
    print(f"Testing GET {test_url}")
    resp = get_with_retry(test_url, params=test_params)
    print(f"Status code: {resp.status_code}")
    print(f"Response (first 200 chars): {resp.text[:200]}")
