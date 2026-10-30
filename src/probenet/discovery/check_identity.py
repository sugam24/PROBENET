
import json
from collections import Counter
from pathlib import Path

from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.identity import logical_event_key, payload_hash

DATA_DIR = Path("data/raw")
MEASUREMENT_IDS = [1001, 1004, 1005]


def main():
    seen = {}
    stats = Counter()

    for measurement_id in MEASUREMENT_IDS:
        path = DATA_DIR / f"measurement_{measurement_id}.json"

        print(f"\nAnalyzing measurement {measurement_id}...")

        with path.open(encoding="utf-8") as file:
            events = json.load(file)

        for payload in events:
            stats["total"] += 1

            try:
                event = AtlasPingResult.model_validate(payload)
            except ValueError:
                stats["rejected"] += 1
                continue

            key = logical_event_key(event)
            fingerprint = payload_hash(event)

            if key not in seen:
                seen[key] = fingerprint
                stats["unique"] += 1

            elif seen[key] == fingerprint:
                stats["duplicates"] += 1

            else:
                stats["conflicts"] += 1
                if stats["conflicts"] <= 3:
                    print(f"Conflicting key: {key}")

    print("\n=== Identity Analysis Summary ===")

    for name in (
        "total",
        "unique",
        "duplicates",
        "conflicts",
        "rejected",
    ):
        print(f"{name}: {stats[name]}")

    print(f"Distinct logical keys: {len(seen)}")


if __name__ == "__main__":
    main()
