
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from pydantic import ValidationError
from websockets.asyncio.client import connect

from probenet.contracts.atlas import AtlasPingResult
from probenet.transforms.ping import normalize_ping

STREAM_URL = "wss://atlas-stream.ripe.net/stream/?client=probenet"
CONFIG_PATH = Path("config/measurements.json")

QUEUE_MAXSIZE = 1000
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


async def read_messages(websocket, queue: asyncio.Queue):
    """Producer: receive WebSocket messages and enqueue them."""
    async for raw_message in websocket:
        received_at = datetime.now(timezone.utc)
        await queue.put((raw_message, received_at))


async def process_messages(queue: asyncio.Queue):
    """Consumer: validate and normalize queued messages."""
    while True:
        raw_message, received_at = await queue.get()

        try:
            message = json.loads(raw_message)

            if not isinstance(message, list) or len(message) != 2:
                log_event("unexpected_message", message_type="unknown")
                continue

            event_type, payload = message

            if event_type != "atlas_result":
                log_event("control_message", event_type=event_type)
                continue

            source = AtlasPingResult.model_validate(payload)
            normalized = normalize_ping(source, received_at)

            log_event(
                "ping_received",
                measurement_id=normalized.measurement_id,
                probe_id=normalized.probe_id,
                event_time=normalized.event_time.isoformat(),
                packet_loss_ratio=normalized.packet_loss_ratio,
                average_rtt_ms=normalized.average_rtt_ms,
            )

        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            log_event(
                "invalid_message",
                error_type=type(exc).__name__,
            )

        finally:
            queue.task_done()


async def run_pipeline(websocket, queue: asyncio.Queue):
    """Run producer and consumer with controlled shutdown."""
    consumer = asyncio.create_task(process_messages(queue))

    try:
        await read_messages(websocket, queue)

        # Process remaining queued messages after the producer finishes.
        await queue.join()

    finally:
        # Stop the consumer even if the producer fails.
        consumer.cancel()

        try:
            await consumer
        except asyncio.CancelledError:
            pass


async def collect():
    """Keep the RIPE Atlas subscriber running across disconnections."""
    measurement_ids = load_measurements()
    retry_delay = RECONNECT_INITIAL_DELAY

    while True:
        # Reset connection tracking for each attempt.
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

                    await websocket.send(json.dumps(subscription))

                    log_event(
                        "subscription_sent",
                        measurement_id=measurement_id,
                    )

                await run_pipeline(websocket, queue)

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
            # Unexpected programming errors should remain visible.
            log_event(
                "collector_failed",
                error_type=type(exc).__name__,
            )
            raise

        finally:
            # Reset the retry delay only after a stable connection.
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
