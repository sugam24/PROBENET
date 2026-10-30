
import json
from pathlib import Path

from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.identity import logical_event_key, payload_hash

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "ping_success.json"
)


def load_event() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_identical_events_have_same_identity_and_hash():
    payload = load_event()

    first = AtlasPingResult.model_validate(payload)
    second = AtlasPingResult.model_validate(payload)

    assert logical_event_key(first) == logical_event_key(second)
    assert payload_hash(first) == payload_hash(second)


def test_modified_payload_has_same_key_but_different_hash():
    original = load_event()
    modified = load_event()

    modified["avg"] = 45.20

    first = AtlasPingResult.model_validate(original)
    second = AtlasPingResult.model_validate(modified)

    assert logical_event_key(first) == logical_event_key(second)
    assert payload_hash(first) != payload_hash(second)


def test_json_field_order_does_not_change_hash():
    original = load_event()

    reordered = dict(reversed(list(original.items())))

    first = AtlasPingResult.model_validate(original)
    second = AtlasPingResult.model_validate(reordered)

    assert payload_hash(first) == payload_hash(second)


def test_storage_timestamp_does_not_change_hash():
    original = load_event()
    modified = load_event()

    modified["stored_timestamp"] = 1793999999

    first = AtlasPingResult.model_validate(original)
    second = AtlasPingResult.model_validate(modified)

    assert logical_event_key(first) == logical_event_key(second)
    assert payload_hash(first) == payload_hash(second)


def test_different_probe_has_different_logical_key():
    original = load_event()
    modified = load_event()

    modified["prb_id"] = 99999

    first = AtlasPingResult.model_validate(original)
    second = AtlasPingResult.model_validate(modified)

    assert logical_event_key(first) != logical_event_key(second)
