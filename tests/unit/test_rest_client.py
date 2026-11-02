
"""Tests for bounded historical REST requests."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from probenet.backfill.rest_client import (
    build_results_url,
    parse_utc,
)


def test_valid_bounded_request():
    start = parse_utc("2026-10-31T10:00:00Z")
    stop = parse_utc("2026-10-31T10:02:00Z")

    url = build_results_url(1001, start, stop)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.path == "/api/v2/measurements/1001/results/"
    assert int(params["stop"][0]) - int(params["start"][0]) == 120


def test_probe_filters():
    start = parse_utc("2026-10-31T10:00:00Z")
    stop = start + timedelta(minutes=2)

    url = build_results_url(
        1001, start, stop, probe_ids=[7475, 7670]
    )

    assert parse_qs(urlparse(url).query)["probe_ids"] == [
        "7475,7670"
    ]


def test_reject_unbounded_request():
    start = parse_utc("2026-10-31T10:00:00Z")
    stop = start + timedelta(hours=24)

    with pytest.raises(ValueError, match="15 minutes"):
        build_results_url(1001, start, stop)


def test_reject_reversed_interval():
    start = parse_utc("2026-10-31T10:02:00Z")
    stop = parse_utc("2026-10-31T10:00:00Z")

    with pytest.raises(ValueError):
        build_results_url(1001, start, stop)


def test_reject_naive_timestamp():
    with pytest.raises(ValueError, match="timezone"):
        parse_utc("2026-10-31T10:00:00")


def test_reject_future_interval():
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    stop = start + timedelta(minutes=2)

    with pytest.raises(ValueError, match="future"):
        build_results_url(1001, start, stop)


def test_reject_invalid_measurement():
    start = parse_utc("2026-10-31T10:00:00Z")
    stop = start + timedelta(minutes=2)

    with pytest.raises(ValueError, match="Measurement ID"):
        build_results_url(0, start, stop)
