
import asyncio

import httpx

BASE_URL = "https://atlas.ripe.net/api/v2"


async def fetch_measurements(limit: int = 10):
    """Discover ongoing public ping measurements."""

    measurements = []
    url = f"{BASE_URL}/measurements/"

    params = {
        "type": "ping",
        "status": 2,
        "is_public": "true",
        "page_size": 100,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url and len(measurements) < limit:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            for measurement in data.get("results", []):
                if measurement.get("is_public") is not True:
                    continue

                if measurement.get("type") != "ping":
                    continue

                measurements.append(measurement)

                if len(measurements) >= limit:
                    break

            url = data.get("next")
            params = None

    return measurements


async def main():
    measurements = await fetch_measurements(limit=10)

    print(f"\nFound {len(measurements)} public ping measurements\n")

    for measurement in measurements:
        status = measurement.get("status") or {}

        print(
            f"ID: {measurement.get('id')} | "
            f"Target: {measurement.get('target')} | "
            f"Interval: {measurement.get('interval')}s | "
            f"Status: {status.get('name', 'Unknown')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
