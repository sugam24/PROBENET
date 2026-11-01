
from dataclasses import dataclass, field
from time import monotonic


@dataclass
class CollectorMetrics:
    """Track collector health and processing performance."""

    messages_received: int = 0
    pings_processed: int = 0
    invalid_messages: int = 0
    control_messages: int = 0

    pings_inserted: int = 0
    pings_duplicate: int = 0
    pings_conflicting: int = 0
    storage_errors: int = 0

    maximum_queue_size: int = 0
    started_at: float = field(default_factory=monotonic)

    def record_received(self, queue_size: int) -> None:
        self.messages_received += 1
        self.maximum_queue_size = max(
            self.maximum_queue_size,
            queue_size,
        )

    def record_ping(self) -> None:
        self.pings_processed += 1

    def record_invalid(self) -> None:
        self.invalid_messages += 1

    def record_control(self) -> None:
        self.control_messages += 1

    def record_storage_result(self, result: str) -> None:
        if result == "inserted":
            self.pings_inserted += 1
        elif result == "duplicate":
            self.pings_duplicate += 1
        else:
            raise ValueError(f"Unexpected storage result: {result}")

    def record_conflict(self) -> None:
        self.pings_conflicting += 1

    def record_storage_error(self) -> None:
        self.storage_errors += 1

    def snapshot(self, current_queue_size: int = 0) -> dict:
        elapsed = max(monotonic() - self.started_at, 0.001)

        return {
            "uptime_seconds": round(elapsed, 2),
            "messages_received": self.messages_received,
            "pings_processed": self.pings_processed,
            "invalid_messages": self.invalid_messages,
            "control_messages": self.control_messages,
            "pings_inserted": self.pings_inserted,
            "pings_duplicate": self.pings_duplicate,
            "pings_conflicting": self.pings_conflicting,
            "storage_errors": self.storage_errors,
            "current_queue_size": current_queue_size,
            "maximum_queue_size": self.maximum_queue_size,
            "average_pings_per_second": round(
                self.pings_processed / elapsed,
                2,
            ),
        }
