
"""Unit tests for incremental historical JSONL processing."""

import json
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest

from probenet.backfill import rest_client
from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.normalized import NormalizedPing


def make_ping(
    probe_id: int = 7475,
    received: int = 2,
) -> dict:
    """Create a minimal valid RIPE Atlas ping result."""
    return {
        "msm_id": 1001,
        "prb_id": probe_id,
        "timestamp": 1793440808,
        "type": "ping",
        "sent": 3,
        "rcvd": received,
        "result": [
            {"rtt": 12.5},
            {"rtt": 14.5},
            {"x": "*"},
        ],
        "min": 12.5,
        "max": 14.5,
        "avg": 13.5,
        "af": 4,
    }


def make_jsonl(*records: dict) -> bytes:
    return b"".join(
        (json.dumps(record) + "\n").encode("utf-8")
        for record in records
    )


def test_stream_yields_validated_normalized_pings(monkeypatch):
    data = make_jsonl(
        make_ping(probe_id=7475),
        make_ping(probe_id=7670),
    )

    monkeypatch.setattr(
        rest_client,
        "urlopen",
        lambda *args, **kwargs: BytesIO(data),
    )

    results = list(stream_for_test())

    assert len(results) == 2

    source, normalized = results[0]

    assert isinstance(source, AtlasPingResult)
    assert isinstance(normalized, NormalizedPing)

    assert normalized.measurement_id == 1001
    assert normalized.probe_id == 7475
    assert normalized.packets_sent == 3
    assert normalized.packets_received == 2
    assert normalized.packet_loss_ratio == pytest.approx(1 / 3)
    assert normalized.average_rtt_ms == 13.5
    assert normalized.event_time.tzinfo is not None
    assert normalized.received_at.tzinfo is not None

    assert results[1][1].probe_id == 7670


def stream_for_test():
    return rest_client.stream_results(
        "https://atlas.ripe.net/api/v2/measurements/1001/results/"
    )


def test_stream_is_lazy(monkeypatch):
    class TrackingResponse(BytesIO):
        def __init__(self, content):
            super().__init__(content)
            self.read_calls = 0

        def readline(self, size=-1):
            self.read_calls += 1
            return super().readline(size)

    response = TrackingResponse(
        make_jsonl(
            make_ping(probe_id=7475),
            make_ping(probe_id=7670),
        )
    )

    monkeypatch.setattr(
        rest_client,
        "urlopen",
        lambda *args, **kwargs: response,
    )

    iterator = stream_for_test()

    assert response.read_calls == 0

    first_source, first_normalized = next(iterator)

    assert first_source.prb_id == 7475
    assert first_normalized.probe_id == 7475
    assert response.read_calls == 1

    next(iterator)
    assert response.read_calls == 2

    with pytest.raises(StopIteration):
        next(iterator)

    assert response.read_calls == 3


def test_stream_rejects_malformed_json(monkeypatch):
    data = b'{"msm_id": 1001, broken-json\n'

    monkeypatch.setattr(
        rest_client,
        "urlopen",
        lambda *args, **kwargs: BytesIO(data),
    )

    with pytest.raises(ValueError, match="Invalid JSON"):
        list(stream_for_test())


def test_stream_rejects_invalid_ping(monkeypatch):
    invalid = make_ping()
    invalid["rcvd"] = 5

    monkeypatch.setattr(
        rest_client,
        "urlopen",
        lambda *args, **kwargs: BytesIO(
            make_jsonl(invalid)
        ),
    )

    with pytest.raises(ValueError, match="Invalid ping"):
        list(stream_for_test())


def test_stream_rejects_oversized_line(monkeypatch):
    data = b"x" * (rest_client.MAX_LINE_BYTES + 1)

    monkeypatch.setattr(
        rest_client,
        "urlopen",
        lambda *args, **kwargs: BytesIO(data),
    )

    with pytest.raises(ValueError, match="1 MiB"):
        list(stream_for_test())


def test_stream_request_uses_jsonl_format():
    start = rest_client.parse_utc("2026-10-31T10:00:00Z")
    stop = rest_client.parse_utc("2026-10-31T10:02:00Z")

    url = rest_client.build_results_url(
        1001,
        start,
        stop,
        response_format="txt",
    )

    params = parse_qs(urlparse(url).query)

    assert params["format"] == ["txt"]
