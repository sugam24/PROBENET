import json

from sqlalchemy import text
from sqlalchemy.engine import Engine

from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.identity import payload_hash
from probenet.contracts.normalized import NormalizedPing


class PayloadConflictError(Exception):
    """Same logical observation identity, different payload hash."""


class _DuplicatePing(Exception):
    """Internal signal to roll back an identical duplicate."""


def save_ping(
    engine: Engine,
    source: AtlasPingResult,
    normalized: NormalizedPing,
) -> str:
    """Persist one ping atomically.

    Returns:
        "inserted": A new canonical observation was saved.
        "duplicate": An identical observation already exists.

    Raises:
        PayloadConflictError: Same key, different source payload.
    """

    if (
        normalized.measurement_id != source.msm_id
        or normalized.probe_id != source.prb_id
        or int(normalized.event_time.timestamp()) != source.timestamp
    ):
        raise ValueError("Source and normalized event identities differ")

    event_hash = payload_hash(source)

    raw_payload = json.dumps(
        source.model_dump(mode="json"),
        sort_keys=True,
    )

    try:
        with engine.begin() as connection:
            raw_id = connection.execute(
                text("""
                    INSERT INTO raw_results (
                        measurement_id,
                        probe_id,
                        event_time,
                        received_at,
                        payload,
                        payload_hash
                    )
                    VALUES (
                        :measurement_id,
                        :probe_id,
                        :event_time,
                        :received_at,
                        CAST(:payload AS JSONB),
                        :payload_hash
                    )
                    RETURNING id
                """),
                {
                    "measurement_id": normalized.measurement_id,
                    "probe_id": normalized.probe_id,
                    "event_time": normalized.event_time,
                    "received_at": normalized.received_at,
                    "payload": raw_payload,
                    "payload_hash": event_hash,
                },
            ).scalar_one()

            fact_id = connection.execute(
                text("""
                    INSERT INTO fact_ping (
                        raw_result_id,
                        measurement_id,
                        probe_id,
                        event_time,
                        received_at,
                        address_family,
                        packets_sent,
                        packets_received,
                        packet_loss_ratio,
                        average_rtt_ms,
                        minimum_rtt_ms,
                        maximum_rtt_ms
                    )
                    VALUES (
                        :raw_result_id,
                        :measurement_id,
                        :probe_id,
                        :event_time,
                        :received_at,
                        :address_family,
                        :packets_sent,
                        :packets_received,
                        :packet_loss_ratio,
                        :average_rtt_ms,
                        :minimum_rtt_ms,
                        :maximum_rtt_ms
                    )
                    ON CONFLICT ON CONSTRAINT uq_fact_ping_logical_event
                    DO NOTHING
                    RETURNING id
                """),
                {
                    "raw_result_id": raw_id,
                    **normalized.model_dump(mode="python"),
                },
            ).scalar_one_or_none()

            if fact_id is None:
                existing_hash = connection.execute(
                    text("""
                        SELECT r.payload_hash
                        FROM fact_ping AS f
                        JOIN raw_results AS r
                          ON r.id = f.raw_result_id
                        WHERE f.measurement_id = :measurement_id
                          AND f.probe_id = :probe_id
                          AND f.event_time = :event_time
                    """),
                    {
                        "measurement_id": normalized.measurement_id,
                        "probe_id": normalized.probe_id,
                        "event_time": normalized.event_time,
                    },
                ).scalar_one()

                if existing_hash != event_hash:
                    raise PayloadConflictError(
                        "Existing observation has a different payload hash"
                    )

                raise _DuplicatePing

    except _DuplicatePing:
        return "duplicate"

    return "inserted"