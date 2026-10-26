
import asyncio
import json

from websockets.asyncio.client import connect


STREAM_URL = (
    "wss://atlas-stream.ripe.net/stream/"
    "?client=probenet-learning"
)

MEASUREMENT_ID = 1001


async def collect_results():
    """Connect to RIPE Atlas and receive live measurements."""

    async with connect(STREAM_URL) as websocket:
        print("Connected to RIPE Atlas!")

        subscription = [
            "atlas_subscribe",
            {
                "streamType": "result",
                "msm": MEASUREMENT_ID,
            },
        ]

        await websocket.send(json.dumps(subscription))
        print(f"Subscribed to measurement {MEASUREMENT_ID}")

        async for message in websocket:
            data = json.loads(message)

            print(json.dumps(data, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(collect_results())
    except KeyboardInterrupt:
        print("\nCollector stopped.")
