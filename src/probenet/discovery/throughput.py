
import asyncio
import json
import time

from websockets.asyncio.client import connect


STREAM_URL = "wss://atlas-stream.ripe.net/stream/?client=probenet-throughput"
MEASUREMENT_ID = 1001
DURATION_SECONDS = 60


async def main():
    total_events = 0
    total_bytes = 0

    async with connect(STREAM_URL) as websocket:
        await websocket.send(
            json.dumps(
                [
                    "atlas_subscribe",
                    {
                        "streamType": "result",
                        "msm": MEASUREMENT_ID,
                    },
                ]
            )
        )

        print(f"Measuring stream {MEASUREMENT_ID} for 60 seconds...")

        start = time.monotonic()
        deadline = start + DURATION_SECONDS

        while True:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            try:
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                break

            payload = json.loads(message)

            # Ignore subscription acknowledgements and other
            # control messages when counting measurement results.
            if not (
                isinstance(payload, list)
                and len(payload) == 2
                and payload[0] == "atlas_result"
            ):
                continue

            total_events += 1
            total_bytes += len(message.encode("utf-8"))

    elapsed = time.monotonic() - start

    print("\n--- Throughput Report ---")
    print(f"Duration: {elapsed:.2f} seconds")
    print(f"Total events: {total_events}")
    print(f"Total bytes: {total_bytes:,}")
    print(f"Events/sec: {total_events / elapsed:.2f}")
    print(f"KB/sec: {total_bytes / elapsed / 1024:.2f}")

    if total_events:
        print(f"Average event size: {total_bytes / total_events:.0f} bytes")


if __name__ == "__main__":
    asyncio.run(main())
