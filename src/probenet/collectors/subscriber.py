
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from websockets.asyncio.client import connect

from probenet.contracts.atlas import AtlasPingResult
from probenet.transforms.ping import normalize_ping

STREAM_URL = "wss://atlas-stream.ripe.net/stream/?client=probenet"
CONFIG_PATH = Path("config/measurements.json")
QUEUE_MAXSIZE = 1000

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
            log_event("invalid_message", error_type=type(exc).__name__)

        finally:
            queue.task_done()


async def collect():
    """Subscribe to selected measurements and process results."""
    measurement_ids = load_measurements()

    queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)

    async with connect(STREAM_URL) as websocket:
        log_event("connected", measurements=measurement_ids)

        for measurement_id in measurement_ids:
            subscription = [
                "atlas_subscribe",
                {"streamType": "result", "msm": measurement_id},
            ]

            await websocket.send(json.dumps(subscription))
            log_event("subscription_sent", measurement_id=measurement_id)

        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(read_messages(websocket, queue))
            tasks.create_task(process_messages(queue))


if __name__ == "__main__":
    try:
        asyncio.run(collect())
    except KeyboardInterrupt:
        print("\nCollector stopped.")
