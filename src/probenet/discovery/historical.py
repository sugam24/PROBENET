
import asyncio
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


BASE_URL = "https://atlas.ripe.net/api/v2"
MEASUREMENT_IDS = [1001, 1004, 1005]
OUTPUT_DIR = Path("data/raw")


async def fetch_history(client, measurement_id, start, stop):
    """Retrieve a bounded historical measurement interval."""

    response = await client.get(
        f"{BASE_URL}/measurements/{measurement_id}/results/",
        params={
            "start": int(start.timestamp()),
            "stop": int(stop.timestamp()),
        },
    )
    response.raise_for_status()
    return response.json()


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stop = datetime.now(timezone.utc) - timedelta(minutes=10)
    start = stop - timedelta(minutes=10)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for measurement_id in MEASUREMENT_IDS:
            print(f"\nFetching measurement {measurement_id}...")

            results = await fetch_history(
                client, measurement_id, start, stop
            )

            output_file = OUTPUT_DIR / f"measurement_{measurement_id}.json"

            with output_file.open("w") as file:
                json.dump(results, file, indent=2)

            probe_ids = {
                result["prb_id"]
                for result in results
                if "prb_id" in result
            }

            result_types = Counter(
                result.get("type", "unknown")
                for result in results
            )

            print(f"Total results: {len(results)}")
            print(f"Unique probes: {len(probe_ids)}")
            print(f"Result types: {dict(result_types)}")
            print(f"Saved: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
