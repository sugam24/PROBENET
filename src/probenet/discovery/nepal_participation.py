
import asyncio
import json
from pathlib import Path

from probenet.discovery.probes import fetch_probes

MEASUREMENT_IDS = [1001, 1004, 1005]
DATA_DIR = Path("data/raw")


async def main():
    probes = await fetch_probes("NP")

    connected_probes = {
        probe["id"]: probe
        for probe in probes
        if probe.get("status", {}).get("name") == "Connected"
    }

    print(f"Connected Nepal probes: {len(connected_probes)}")

    for measurement_id in MEASUREMENT_IDS:
        file_path = DATA_DIR / f"measurement_{measurement_id}.json"

        with file_path.open() as file:
            results = json.load(file)

        participating_ids = {
            result["prb_id"]
            for result in results
            if "prb_id" in result
        }

        nepal_ids = participating_ids & connected_probes.keys()

        asns = {
            connected_probes[probe_id].get("asn_v4")
            for probe_id in nepal_ids
            if connected_probes[probe_id].get("asn_v4") is not None
        }

        print(f"\nMeasurement {measurement_id}")
        print(f"  Total participating probes: {len(participating_ids)}")
        print(f"  Connected Nepal probes participating: {len(nepal_ids)}")
        print(f"  Distinct Nepal IPv4 ASNs: {len(asns)}")
        print(f"  Nepal probe IDs: {sorted(nepal_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
