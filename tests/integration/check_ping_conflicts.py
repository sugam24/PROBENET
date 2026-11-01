
from datetime import datetime, timezone

from sqlalchemy import text

from probenet.contracts.atlas import AtlasPingResult
from probenet.storage.database import get_engine
from probenet.storage.ping_repository import (
    PayloadConflictError,
    save_ping,
)
from probenet.transforms.ping import normalize_ping


def build_event(avg: float) -> AtlasPingResult:
    return AtlasPingResult.model_validate(
        {
            "msm_id": 1001,
            "prb_id": 7475,
            "timestamp": 1700000001,
            "type": "ping",
            "sent": 3,
            "rcvd": 3,
            "result": [
                {"rtt": avg},
                {"rtt": avg},
                {"rtt": avg},
            ],
            "min": avg,
            "max": avg,
            "avg": avg,
        }
    )


def main():
    engine = get_engine()

    original = build_event(42.5)
    conflicting = build_event(55.8)

    original_normalized = normalize_ping(
        original,
        received_at=datetime.now(timezone.utc),
    )
    conflicting_normalized = normalize_ping(
        conflicting,
        received_at=datetime.now(timezone.utc),
    )

    params = {
        "measurement_id": original.msm_id,
        "probe_id": original.prb_id,
        "event_time": original_normalized.event_time,
    }

    try:
        first = save_ping(engine, original, original_normalized)
        print(f"Original insertion: {first}")

        for attempt in range(2):
            try:
                save_ping(engine, conflicting, conflicting_normalized)
            except PayloadConflictError:
                print(f"Conflict detected on attempt {attempt + 1}")
            else:
                raise AssertionError("Expected PayloadConflictError")

        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM fact_ping
                         WHERE measurement_id = :measurement_id
                           AND probe_id = :probe_id
                           AND event_time = :event_time) AS fact_count,

                        (SELECT COUNT(*) FROM raw_results
                         WHERE measurement_id = :measurement_id
                           AND probe_id = :probe_id
                           AND event_time = :event_time) AS raw_count,

                        (SELECT COUNT(*)
                         FROM ping_conflicts AS c
                         JOIN fact_ping AS f
                           ON f.raw_result_id = c.canonical_raw_result_id
                         WHERE f.measurement_id = :measurement_id
                           AND f.probe_id = :probe_id
                           AND f.event_time = :event_time) AS conflict_count,

                        (SELECT average_rtt_ms FROM fact_ping
                         WHERE measurement_id = :measurement_id
                           AND probe_id = :probe_id
                           AND event_time = :event_time) AS canonical_rtt
                """),
                params,
            ).one()

        print(f"Canonical rows: {result.fact_count}")
        print(f"Raw rows: {result.raw_count}")
        print(f"Conflict records: {result.conflict_count}")
        print(f"Canonical RTT: {result.canonical_rtt} ms")

        assert first == "inserted"
        assert result.fact_count == 1
        assert result.raw_count == 1
        assert result.conflict_count == 1
        assert result.canonical_rtt == 42.5

        print("Conflict audit test passed!")

    finally:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    DELETE FROM ping_conflicts
                    WHERE canonical_raw_result_id IN (
                        SELECT raw_result_id
                        FROM fact_ping
                        WHERE measurement_id = :measurement_id
                          AND probe_id = :probe_id
                          AND event_time = :event_time
                    )
                """),
                params,
            )

            connection.execute(
                text("""
                    DELETE FROM fact_ping
                    WHERE measurement_id = :measurement_id
                      AND probe_id = :probe_id
                      AND event_time = :event_time
                """),
                params,
            )

            connection.execute(
                text("""
                    DELETE FROM raw_results
                    WHERE measurement_id = :measurement_id
                      AND probe_id = :probe_id
                      AND event_time = :event_time
                """),
                params,
            )

        engine.dispose()


if __name__ == "__main__":
    main()
