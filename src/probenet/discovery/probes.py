
import asyncio
from collections import Counter

import httpx


BASE_URL = "https://atlas.ripe.net/api/v2"


async def fetch_probes(country_code: str = "NP"):
    """Retrieve all pages of public RIPE Atlas probes."""

    probes = []
    url = f"{BASE_URL}/probes/"
    params = {
        "country_code": country_code,
        "page_size": 100,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            probes.extend(data["results"])

            url = data.get("next")
            params = None

    return probes


async def main():
    probes = await fetch_probes()

    status_counts = Counter(
        probe.get("status", {}).get("name", "Unknown")
        for probe in probes
    )

    connected = [
        probe
        for probe in probes
        if probe.get("status", {}).get("name") == "Connected"
    ]

    unique_asns = {
        probe["asn_v4"]
        for probe in connected
        if probe.get("asn_v4") is not None
    }

    print(f"\nTotal retrieved probes: {len(probes)}")

    print("\nProbe status distribution:")
    for status, count in status_counts.most_common():
        print(f"  {status}: {count}")

    print(f"\nConnected probes: {len(connected)}")
    print(f"Unique connected IPv4 ASNs: {len(unique_asns)}")

    print("\nConnected probe details:")
    for probe in connected:
        print(
            f"  Probe {probe['id']} | "
            f"ASN: {probe.get('asn_v4')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
