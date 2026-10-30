
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from pydantic import ValidationError
from websockets.asyncio.client import connect

from probenet.collectors.metrics import CollectorMetrics
from probenet.collectors.raw_capture import RawCaptureWriter
from probenet.contracts.atlas import AtlasPingResult
from probenet.transforms.ping import normalize_ping

STREAM_URL = "wss://atlas-stream.ripe.net/stream/?client=probenet"
CONFIG_PATH = Path("config/measurements.json")

QUEUE_MAXSIZE = 1000
METRICS_INTERVAL_SECONDS = 10
RECONNECT_INITIAL_DELAY = 1
RECONNECT_MAX_DELAY = 30
CONNECT_TIMEOUT = 15
STABLE_CONNECTION_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("probenet.collector")


def log_event(event: str, **fields):
    """Write a structured JSON log entry."""
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(record))


def load_measurements() -> list[int]:
    """Load measurement IDs from configuration."""
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = json.load(file)

    return config["measurement_ids"]


def create_capture_writer():
    """Create an optional raw capture writer."""
    enabled = os.getenv("PROBENET_CAPTURE_ENABLED", "false").lower()

    if enabled != "true":
        return None

    path = Path(
        os.getenv(
            "PROBENET_CAPTURE_PATH",
            "data/raw/live_capture.jsonl",
        )
    )

    max_events = int(
        os.getenv("PROBENET_CAPTURE_MAX_EVENTS", "1000")
    )

    if path.exists():
        raise FileExistsError(
            f"Capture file already exists: {path}"
        )

    return RawCaptureWriter(path=path, max_events=max_events)


async def read_messages(
    websocket,
    queue: asyncio.Queue,
    capture_writer=None,
    metrics=None,
):
    """Receive, optionally capture, and enqueue WebSocket messages."""
    async for raw_message in websocket:
        received_at = datetime.now(timezone.utc)

        if capture_writer is not None:
            capture_writer.write(raw_message, received_at)

        await queue.put((raw_message, received_at))

        if metrics is not None:
            metrics.record_received(queue.qsize())


async def process_messages(queue: asyncio.Queue, metrics=None):
    """Validate and normalize queued messages."""
    while True:
        raw_message, received_at = await queue.get()

        try:
            message = json.loads(raw_message)

            if not isinstance(message, list) or len(message) != 2:
                if metrics is not None:
                    metrics.record_invalid()

                log_event(
                    "unexpected_message",
                    message_type="unknown",
                )
                continue

            event_type, payload = message

            if event_type != "atlas_result":
                if metrics is not None:
                    metrics.record_control()

                log_event(
                    "control_message",
                    event_type=event_type,
                )
                continue

            source = AtlasPingResult.model_validate(payload)
            normalized = normalize_ping(source, received_at)

            if metrics is not None:
                metrics.record_ping()

            log_event(
                "ping_received",
                measurement_id=normalized.measurement_id,
                probe_id=normalized.probe_id,
                event_time=normalized.event_time.isoformat(),
                packet_loss_ratio=normalized.packet_loss_ratio,
                average_rtt_ms=normalized.average_rtt_ms,
            )

        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            if metrics is not None:
                metrics.record_invalid()

            log_event(
                "invalid_message",
                error_type=type(exc).__name__,
            )

        finally:
            queue.task_done()


async def report_metrics(
    queue: asyncio.Queue,
    metrics: CollectorMetrics,
):
    """Periodically publish collector health metrics."""
    while True:
        await asyncio.sleep(METRICS_INTERVAL_SECONDS)

        log_event(
            "collector_metrics",
            **metrics.snapshot(queue.qsize()),
        )


async def run_pipeline(
    websocket,
    queue: asyncio.Queue,
    capture_writer=None,
    metrics=None,
):
    """Run the producer, consumer and optional metrics reporter."""
    consumer = asyncio.create_task(process_messages(queue, metrics))

    reporter = None

    if metrics is not None:
        reporter = asyncio.create_task(report_metrics(queue, metrics))

    try:
        await read_messages(
            websocket,
            queue,
            capture_writer,
            metrics,
        )

        # Drain queued messages after a normal WebSocket closure.
        await queue.join()

    finally:
        consumer.cancel()

        tasks = [consumer]

        if reporter is not None:
            reporter.cancel()
            tasks.append(reporter)

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        if metrics is not None:
            log_event(
                "collector_metrics_final",
                **metrics.snapshot(queue.qsize()),
            )


async def collect():
    """Keep the RIPE Atlas collector running across disconnections."""
    measurement_ids = load_measurements()
    retry_delay = RECONNECT_INITIAL_DELAY
    capture_writer = create_capture_writer()
    metrics = CollectorMetrics()

    while True:
        connected_at = None

        try:
            queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)

            async with connect(
                STREAM_URL,
                open_timeout=CONNECT_TIMEOUT,
            ) as websocket:
                connected_at = monotonic()

                log_event(
                    "connected",
                    measurements=measurement_ids,
                )

                for measurement_id in measurement_ids:
                    subscription = [
                        "atlas_subscribe",
                        {
                            "streamType": "result",
                            "msm": measurement_id,
                        },
                    ]

                    await websocket.send(
                        json.dumps(subscription)
                    )

                    log_event(
                        "subscription_sent",
                        measurement_id=measurement_id,
                    )

                await run_pipeline(
                    websocket,
                    queue,
                    capture_writer,
                    metrics,
                )

                log_event(
                    "connection_closed",
                    reason="stream_ended",
                )

        except (OSError, TimeoutError, ConnectionError) as exc:
            log_event(
                "connection_error",
                error_type=type(exc).__name__,
                retry_delay_seconds=retry_delay,
            )

        except Exception as exc:
            log_event(
                "collector_failed",
                error_type=type(exc).__name__,
            )
            raise

        finally:
            if (
                connected_at is not None
                and monotonic() - connected_at >= STABLE_CONNECTION_SECONDS
            ):
                retry_delay = RECONNECT_INITIAL_DELAY

        log_event(
            "reconnecting",
            delay_seconds=retry_delay,
        )

        await asyncio.sleep(retry_delay)

        retry_delay = min(
            retry_delay * 2,
            RECONNECT_MAX_DELAY,
        )


if __name__ == "__main__":
    try:
        asyncio.run(collect())
    except KeyboardInterrupt:
        print("\nCollector stopped.")
