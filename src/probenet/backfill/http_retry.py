
"""HTTP request retries for RIPE Atlas historical retrieval."""

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError

MAX_ATTEMPTS = 4
MAX_RETRY_DELAY_SECONDS = 120

RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


def retry_after_seconds(value: str | None) -> float | None:
    """Parse Retry-After as seconds or an HTTP-date."""
    if value is None:
        return None

    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_date = parsedate_to_datetime(value)
            if retry_date.tzinfo is None:
                retry_date = retry_date.replace(tzinfo=timezone.utc)

            seconds = (
                retry_date - datetime.now(timezone.utc)
            ).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None

    return max(0.0, seconds)


def open_with_retries(request, *, opener, timeout: int = 30):
    """Retry transient failures before returning an HTTP response.

    The caller owns and must close the returned response.

    A response that fails after reading begins is not restarted here.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return opener(request, timeout=timeout)

        except HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUSES:
                raise

            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"HTTP {exc.code}: exhausted "
                    f"{MAX_ATTEMPTS} attempts"
                ) from exc

            delay = 2 ** (attempt - 1)

            if exc.code in {429, 503}:
                retry_after = retry_after_seconds(
                    exc.headers.get("Retry-After")
                    if exc.headers is not None
                    else None
                )

                if retry_after is not None:
                    delay = retry_after

            if delay > MAX_RETRY_DELAY_SECONDS:
                raise RuntimeError(
                    "Server requested a retry delay exceeding "
                    "the configured 120-second safety limit."
                ) from exc

            time.sleep(delay)

        except (URLError, TimeoutError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Network failure: exhausted "
                    f"{MAX_ATTEMPTS} attempts"
                ) from exc

            delay = 2 ** (attempt - 1)
            time.sleep(delay)

    raise RuntimeError("Unexpected retry-loop termination")
