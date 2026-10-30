
from datetime import datetime, timezone

from probenet.collectors.raw_capture import (
    RawCaptureWriter,
    replay_capture,
)


def test_capture_and_replay_round_trip(tmp_path):
    """Captured messages should replay without modification."""
    capture_path = tmp_path / "capture.jsonl"

    writer = RawCaptureWriter(
        path=capture_path,
        max_events=10,
    )

    received_at = datetime(
        2026, 10, 30, 10, 0, 0, tzinfo=timezone.utc
    )

    messages = [
        '["atlas_result", {"msm_id": 1001}]',
        '["atlas_result", {"msm_id": 1004}]',
        '["atlas_result", {"msm_id": 1005}]',
    ]

    for message in messages:
        assert writer.write(message, received_at)

    replayed = list(replay_capture(capture_path))

    assert len(replayed) == 3
    assert [message for message, _ in replayed] == messages
    assert all(timestamp == received_at for _, timestamp in replayed)


def test_capture_respects_event_limit(tmp_path):
    """The writer must stop after its configured event limit."""
    capture_path = tmp_path / "limited.jsonl"

    writer = RawCaptureWriter(
        path=capture_path,
        max_events=2,
    )

    received_at = datetime.now(timezone.utc)

    assert writer.write("event_1", received_at)
    assert writer.write("event_2", received_at)

    # A third event must not be written.
    assert not writer.write("event_3", received_at)

    assert writer.written == 2
    assert len(list(replay_capture(capture_path))) == 2
