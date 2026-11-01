
"""ProbeNet REST API for network measurement observability."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from probenet.storage.database import get_engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Response models
# ---------------------------------------------------------


class HealthResponse(BaseModel):
    status: str


class MeasurementResponse(BaseModel):
    measurement_id: int
    target: str | None
    measurement_type: str | None
    interval_seconds: int | None
    status: str | None
    is_public: bool | None


class HourlyMetricsResponse(BaseModel):
    measurement_id: int
    hour_utc: datetime
    observation_count: int
    observations_with_rtt: int
    unique_probes: int
    total_packets_sent: int
    total_packets_received: int
    total_packets_lost: int
    average_rtt_ms: float | None
    packet_loss_ratio: float | None


class PingResponse(BaseModel):
    measurement_id: int
    probe_id: int
    event_time: datetime
    received_at: datetime
    packets_sent: int
    packets_received: int
    loss_ratio: float | None
    average_rtt_ms: float | None
    min_rtt_ms: float | None
    max_rtt_ms: float | None


# ---------------------------------------------------------
# Database lifecycle
# ---------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and dispose the SQLAlchemy engine."""
    engine = get_engine()
    app.state.engine = engine

    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="ProbeNet API",
    description="Real-time network observability using RIPE Atlas.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Database utilities
# ---------------------------------------------------------


def execute_query(
    request: Request,
    query: str,
    parameters: dict | None = None,
) -> list[dict]:
    """Execute a read-only SQL query and return dictionaries."""
    try:
        with request.app.state.engine.connect() as connection:
            result = connection.execute(
                text(query),
                parameters or {},
            )
            return [dict(row) for row in result.mappings().all()]

    except OperationalError:
        logger.exception("Database connection or operation failed")
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily unavailable",
        ) from None

    except SQLAlchemyError:
        logger.exception("Database query execution failed")
        raise HTTPException(
            status_code=500,
            detail="Internal database query error",
        ) from None


def ensure_measurement_exists(
    request: Request,
    measurement_id: int,
) -> None:
    """Raise HTTP 404 for an unknown measurement."""
    rows = execute_query(
        request,
        """
        SELECT measurement_id
        FROM dim_measurement
        WHERE measurement_id = :measurement_id
        """,
        {"measurement_id": measurement_id},
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Measurement {measurement_id} not found",
        )


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
def health_check():
    """Check whether the API application is running."""
    return {"status": "ok"}


# ---------------------------------------------------------
# Measurement metadata endpoint
# ---------------------------------------------------------


@app.get(
    "/measurements",
    response_model=list[MeasurementResponse],
    tags=["Measurements"],
)
def list_measurements(request: Request):
    """Retrieve RIPE Atlas measurement metadata."""
    return execute_query(
        request,
        """
        SELECT
            measurement_id,
            target,
            measurement_type,
            interval_seconds,
            status,
            is_public
        FROM dim_measurement
        ORDER BY measurement_id
        """,
    )


# ---------------------------------------------------------
# Hourly analytics endpoint
# ---------------------------------------------------------


@app.get(
    "/measurements/{measurement_id}/hourly",
    response_model=list[HourlyMetricsResponse],
    tags=["Analytics"],
)
def get_hourly_metrics(
    measurement_id: int,
    request: Request,
    limit: int = Query(default=24, ge=1, le=168),
):
    """Retrieve hourly latency and packet-loss statistics."""
    ensure_measurement_exists(request, measurement_id)

    return execute_query(
        request,
        """
        SELECT
            measurement_id,

            (
                date_trunc(
                    'hour',
                    event_time AT TIME ZONE 'UTC'
                ) AT TIME ZONE 'UTC'
            ) AS hour_utc,

            COUNT(*) AS observation_count,

            COUNT(average_rtt_ms) AS observations_with_rtt,

            COUNT(DISTINCT probe_id) AS unique_probes,

            SUM(packets_sent)::bigint
                AS total_packets_sent,

            SUM(packets_received)::bigint
                AS total_packets_received,

            SUM(packets_sent - packets_received)::bigint
                AS total_packets_lost,

            ROUND(
                AVG(average_rtt_ms)::numeric,
                2
            ) AS average_rtt_ms,

            ROUND(
                SUM(packets_sent - packets_received)::numeric
                / NULLIF(SUM(packets_sent), 0),
                4
            ) AS packet_loss_ratio

        FROM fact_ping

        WHERE measurement_id = :measurement_id

        GROUP BY
            measurement_id,
            hour_utc

        ORDER BY hour_utc DESC

        LIMIT :limit
        """,
        {
            "measurement_id": measurement_id,
            "limit": limit,
        },
    )


# ---------------------------------------------------------
# Recent ping observations endpoint
# ---------------------------------------------------------


@app.get(
    "/measurements/{measurement_id}/pings",
    response_model=list[PingResponse],
    tags=["Observations"],
)
def get_recent_pings(
    measurement_id: int,
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Retrieve recent persisted ping observations."""
    ensure_measurement_exists(request, measurement_id)

    return execute_query(
        request,
        """
        SELECT
            measurement_id,
            probe_id,
            event_time,
            received_at,
            packets_sent,
            packets_received,
            packet_loss_ratio AS loss_ratio,
            average_rtt_ms,
            minimum_rtt_ms AS min_rtt_ms,
            maximum_rtt_ms AS max_rtt_ms
        FROM fact_ping
        WHERE measurement_id = :measurement_id
        ORDER BY event_time DESC, id DESC
        LIMIT :limit
        """,
        {
            "measurement_id": measurement_id,
            "limit": limit,
        },
    )


# ---------------------------------------------------------
# Data freshness and collection continuity
# ---------------------------------------------------------


class MonitoringResponse(BaseModel):
    measurement_id: int
    latest_received_at: datetime | None
    age_seconds: float | None
    freshness_status: str
    recent_observation_count: int
    active_five_minute_buckets: int
    total_five_minute_buckets: int
    continuity_percent: float
    continuity_status: str


@app.get(
    "/measurements/{measurement_id}/monitoring",
    response_model=MonitoringResponse,
    tags=["Monitoring"],
)
def get_measurement_monitoring(
    measurement_id: int,
    request: Request,
):
    """Report observation freshness and recent ingestion continuity."""
    ensure_measurement_exists(request, measurement_id)

    rows = execute_query(
        request,
        """
        WITH clock AS (
            SELECT
                now() AS checked_at,
                date_bin(
                    '5 minutes',
                    now(),
                    TIMESTAMPTZ '2000-01-01 00:00:00+00'
                ) AS current_bucket
        )
        SELECT
            MAX(f.received_at) AS latest_received_at,

            EXTRACT(
                EPOCH FROM (c.checked_at - MAX(f.received_at))
            ) AS age_seconds,

            COUNT(*) FILTER (
                WHERE f.received_at >= c.checked_at - INTERVAL '1 hour'
                  AND f.received_at <= c.checked_at
            ) AS recent_observation_count,

            COUNT(DISTINCT date_bin(
                '5 minutes',
                f.received_at,
                TIMESTAMPTZ '2000-01-01 00:00:00+00'
            )) FILTER (
                WHERE f.received_at >=
                    c.current_bucket - INTERVAL '55 minutes'
                  AND f.received_at <= c.checked_at
            ) AS active_five_minute_buckets

        FROM clock AS c
        LEFT JOIN fact_ping AS f
            ON f.measurement_id = :measurement_id

        GROUP BY c.checked_at, c.current_bucket
        """,
        {"measurement_id": measurement_id},
    )

    row = rows[0]

    age = (
        float(row["age_seconds"])
        if row["age_seconds"] is not None
        else None
    )

    active_buckets = int(row["active_five_minute_buckets"])
    recent_count = int(row["recent_observation_count"])

    total_buckets = 12
    continuity_percent = round(
        active_buckets / total_buckets * 100,
        2,
    )

    # Freshness thresholds are initial operational defaults.
    if age is None:
        freshness_status = "no_data"
    elif age < -60:
        freshness_status = "clock_skew"
    elif age <= 300:
        freshness_status = "fresh"
    elif age <= 900:
        freshness_status = "delayed"
    else:
        freshness_status = "stale"

    # Continuity means an interval contains at least one
    # observation. It does not measure per-probe coverage.
    if active_buckets == 0:
        continuity_status = "no_recent_data"
    elif active_buckets < 6:
        continuity_status = "intermittent"
    else:
        continuity_status = "active"

    return {
        "measurement_id": measurement_id,
        "latest_received_at": row["latest_received_at"],
        "age_seconds": round(age, 2) if age is not None else None,
        "freshness_status": freshness_status,
        "recent_observation_count": recent_count,
        "active_five_minute_buckets": active_buckets,
        "total_five_minute_buckets": total_buckets,
        "continuity_percent": continuity_percent,
        "continuity_status": continuity_status,
    }
