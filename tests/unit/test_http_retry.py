
"""Unit tests for historical HTTP retry behavior."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from probenet.backfill import http_retry


def make_http_error(status, retry_after=None):
    """Create a simulated HTTP error."""
    headers = {}

    if retry_after is not None:
        headers["Retry-After"] = retry_after

    return HTTPError(
        url="https://atlas.ripe.net/api/v2/",
        code=status,
        msg="Simulated HTTP failure",
        hdrs=headers,
        fp=None,
    )


def test_retry_after_429(monkeypatch):
    attempts = []
    delays = []

    def fake_opener(request, timeout):
        attempts.append(1)

        if len(attempts) == 1:
            raise make_http_error(429, "5")

        return BytesIO(b"success")

    monkeypatch.setattr(http_retry.time, "sleep", delays.append)

    response = http_retry.open_with_retries(
        "fake-request",
        opener=fake_opener,
    )

    assert response.read() == b"success"
    assert len(attempts) == 2
    assert delays == [5]


def test_exponential_backoff_on_503(monkeypatch):
    attempts = []
    delays = []

    def fake_opener(request, timeout):
        attempts.append(1)

        if len(attempts) <= 3:
            raise make_http_error(503)

        return BytesIO(b"recovered")

    monkeypatch.setattr(http_retry.time, "sleep", delays.append)

    response = http_retry.open_with_retries(
        "fake-request",
        opener=fake_opener,
    )

    assert response.read() == b"recovered"
    assert len(attempts) == 4
    assert delays == [1, 2, 4]


def test_exhausted_retries_raise_error(monkeypatch):
    attempts = []
    delays = []

    def fake_opener(request, timeout):
        attempts.append(1)
        raise make_http_error(503)

    monkeypatch.setattr(http_retry.time, "sleep", delays.append)

    with pytest.raises(RuntimeError, match="exhausted"):
        http_retry.open_with_retries(
            "fake-request",
            opener=fake_opener,
        )

    assert len(attempts) == 4
    assert delays == [1, 2, 4]


def test_non_retryable_404_fails_immediately(monkeypatch):
    attempts = []

    def fake_opener(request, timeout):
        attempts.append(1)
        raise make_http_error(404)

    monkeypatch.setattr(
        http_retry.time,
        "sleep",
        lambda delay: pytest.fail("Unexpected retry"),
    )

    with pytest.raises(HTTPError) as exc_info:
        http_retry.open_with_retries(
            "fake-request",
            opener=fake_opener,
        )

    assert exc_info.value.code == 404
    assert len(attempts) == 1


def test_transient_network_failure(monkeypatch):
    attempts = []
    delays = []

    def fake_opener(request, timeout):
        attempts.append(1)

        if len(attempts) == 1:
            raise URLError("Simulated network interruption")

        return BytesIO(b"recovered")

    monkeypatch.setattr(http_retry.time, "sleep", delays.append)

    response = http_retry.open_with_retries(
        "fake-request",
        opener=fake_opener,
    )

    assert response.read() == b"recovered"
    assert len(attempts) == 2
    assert delays == [1]


def test_retry_after_http_date():
    future = datetime.now(timezone.utc) + timedelta(seconds=20)
    header = format_datetime(future, usegmt=True)

    seconds = http_retry.retry_after_seconds(header)

    assert seconds is not None
    assert 18 <= seconds <= 20


def test_excessive_retry_after_fails_safely(monkeypatch):
    def fake_opener(request, timeout):
        raise make_http_error(429, "300")

    monkeypatch.setattr(
        http_retry.time,
        "sleep",
        lambda delay: pytest.fail("Unexpected sleep"),
    )

    with pytest.raises(RuntimeError, match="120-second"):
        http_retry.open_with_retries(
            "fake-request",
            opener=fake_opener,
        )
