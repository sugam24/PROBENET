
import asyncio
import json

import httpx


BASE_URL = "https://atlas.ripe.net/api/v2"
MEASUREMENT_IDS = [1001, 1004, 1005]


async def inspect_measurements():
    async with httpx.AsyncClient(timeout=30.0) as client:
        for measurement_id in MEASUREMENT_IDS:
            response = await client.get(
                f"{BASE_URL}/measurements/{measurement_id}/"
            )
            response.raise_for_status()

            data = response.json()

            print(f"\n{'=' * 60}")
            print(f"Measurement ID: {measurement_id}")
            print(f"{'=' * 60}")

            fields = [
                "id",
                "type",
                "target",
                "target_ip",
                "af",
                "interval",
                "packets",
                "size",
                "protocol",
                "is_public",
                "participant_count",
                "probes",
                "status",
            ]

            for field in fields:
                value = data.get(field)
                print(f"{field}: {json.dumps(value)}")


if __name__ == "__main__":
    asyncio.run(inspect_measurements())
