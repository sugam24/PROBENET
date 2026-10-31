from datetime import datetime, timezone

from sqlalchemy import text

from probenet.contracts.atlas import AtlasPingResult
from probenet.storage.database import get_engine
from probenet.storage.ping_repository import save_ping
from probenet.transforms.ping import normalize_ping


def main():
    source = AtlasPingResult.model_validate(
        {
            "msm_id": 1001,
            "prb_id": 7475,
            "timestamp": 1700000000,
            "type": "ping",
            "sent": 3,
            "rcvd": 0,
            "result": [],
            "min": None,
            "max": None,
            "avg": None,
        }
    )

    normalized = normalize_ping(
        source,
        received_at=datetime.now(timezone.utc),
    )

    engine = get_engine()

    params = {
        "measurement_id": source.msm_id,
        "probe_id": source.prb_id,
        "event_time": normalized.event_time,
    }

    try:
        first = save_ping(engine, source, normalized)
        second = save_ping(engine, source, normalized)

        with engine.connect() as connection:
            counts = connection.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM fact_ping
                         WHERE measurement_id = :measurement_id
                           AND probe_id = :probe_id
                           AND event_time = :event_time) AS fact_count,
                        (SELECT COUNT(*) FROM raw_results
                         WHERE measurement_id = :measurement_id
                           AND probe_id = :probe_id
                           AND event_time = :event_time) AS raw_count
                """),
                params,
            ).one()

        print(f"First insertion: {first}")
        print(f"Second insertion: {second}")
        print(f"Canonical rows: {counts.fact_count}")
        print(f"Raw rows: {counts.raw_count}")

        assert first == "inserted"
        assert second == "duplicate"
        assert counts.fact_count == 1
        assert counts.raw_count == 1

        print("Idempotency test passed!")

    finally:
        with engine.begin() as connection:
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