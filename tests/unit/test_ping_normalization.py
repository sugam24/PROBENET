
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from probenet.contracts.atlas import AtlasPingResult
from probenet.transforms.ping import normalize_ping

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
RECEIVED_AT = datetime(2026, 10, 30, tzinfo=timezone.utc)


def load_fixture(filename: str) -> dict:
    """Load a saved RIPE Atlas observation."""
    path = FIXTURE_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def test_successful_ping():
    source = AtlasPingResult.model_validate(
        load_fixture("ping_success.json")
    )

    result = normalize_ping(source, received_at=RECEIVED_AT)

    assert result.measurement_id == 1001
    assert result.probe_id == 10001
    assert result.packets_sent == 3
    assert result.packets_received == 3
    assert result.packet_loss_ratio == 0.0
    assert result.average_rtt_ms == pytest.approx(23.14234966666667)
    assert result.received_at == RECEIVED_AT


def test_partial_packet_loss():
    source = AtlasPingResult.model_validate(
        load_fixture("ping_no_reply.json")
    )

    result = normalize_ping(source, received_at=RECEIVED_AT)

    assert result.packets_sent == 2
    assert result.packets_received == 1
    assert result.packet_loss_ratio == 0.5
    assert result.average_rtt_ms == pytest.approx(1.258507)


def test_malformed_ping_is_rejected():
    payload = load_fixture("ping_malformed.json")

    with pytest.raises(ValidationError):
        AtlasPingResult.model_validate(payload)


def test_extra_fields_are_accepted():
    payload = load_fixture("ping_extra_fields.json")

    source = AtlasPingResult.model_validate(payload)
    result = normalize_ping(source, received_at=RECEIVED_AT)

    assert source.model_extra["future_source_field"] == "example_value"
    assert result.measurement_id == 1001
    assert result.packet_loss_ratio == 0.0


def test_complete_packet_loss():
    payload = load_fixture("ping_success.json")

    payload["sent"] = 3
    payload["rcvd"] = 0
    payload["result"] = [{"x": "*"}] * 3
    payload["min"] = -1
    payload["max"] = -1
    payload["avg"] = -1

    source = AtlasPingResult.model_validate(payload)
    result = normalize_ping(source, received_at=RECEIVED_AT)

    assert result.packet_loss_ratio == 1.0
    assert result.average_rtt_ms is None
    assert result.minimum_rtt_ms is None
    assert result.maximum_rtt_ms is None


def test_zero_packets_sent():
    payload = load_fixture("ping_success.json")

    payload["sent"] = 0
    payload["rcvd"] = 0
    payload["result"] = []
    payload["min"] = -1
    payload["max"] = -1
    payload["avg"] = -1

    source = AtlasPingResult.model_validate(payload)
    result = normalize_ping(source, received_at=RECEIVED_AT)

    assert result.packet_loss_ratio is None
    assert result.average_rtt_ms is None


def test_received_cannot_exceed_sent():
    payload = load_fixture("ping_success.json")

    payload["sent"] = 2
    payload["rcvd"] = 3

    with pytest.raises(ValidationError):
        AtlasPingResult.model_validate(payload)
