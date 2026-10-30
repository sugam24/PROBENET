
import json
from datetime import datetime
from pathlib import Path


class RawCaptureWriter:
    """Write bounded raw WebSocket messages to a JSONL file."""

    def __init__(self, path: Path, max_events: int = 1000):
        if max_events <= 0:
            raise ValueError("max_events must be positive")

        self.path = path
        self.max_events = max_events
        self.written = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, raw_message: str, received_at: datetime) -> bool:
        """Write one event, or return False when the limit is reached."""
        if self.written >= self.max_events:
            return False

        record = {
            "received_at": received_at.isoformat(),
            "raw_message": raw_message,
        }

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")

        self.written += 1
        return True


def replay_capture(path: Path):
    """Yield captured messages with their original receipt timestamps."""
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            record = json.loads(line)

            yield (
                record["raw_message"],
                datetime.fromisoformat(record["received_at"]),
            )
