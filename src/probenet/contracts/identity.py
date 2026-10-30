
import hashlib
import json

from probenet.contracts.atlas import AtlasPingResult


def logical_event_key(event: AtlasPingResult) -> tuple[int, int, int]:
    """Return the provisional identity of one ping observation."""
    return (
        event.msm_id,
        event.prb_id,
        event.timestamp,
    )


def payload_hash(event: AtlasPingResult) -> str:
    """Calculate a deterministic SHA-256 hash of the source payload."""

    payload = event.model_dump(
        mode="json",
        exclude={"stored_timestamp"},
    )

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()
