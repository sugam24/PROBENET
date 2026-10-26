
import json
from collections import Counter
from pathlib import Path


MEASUREMENT_IDS = [1001, 1004, 1005]
DATA_DIR = Path("data/raw")


def analyze_measurement(measurement_id: int):
    path = DATA_DIR / f"measurement_{measurement_id}.json"

    with path.open() as file:
        results = json.load(file)

    field_counts = Counter()
    reply_counts = Counter()
    identity_counts = Counter()

    example_success = None
    example_failure = None

    for event in results:
        field_counts.update(event.keys())

        key = (
            event.get("msm_id"),
            event.get("prb_id"),
            event.get("timestamp"),
        )
        identity_counts[key] += 1

        packets = event.get("result", [])

        if not isinstance(packets, list):
            packets = []

        successful_replies = sum(
            isinstance(packet, dict) and "rtt" in packet
            for packet in packets
        )

        if successful_replies > 0:
            reply_counts["has_reply"] += 1
            if example_success is None:
                example_success = event
        else:
            reply_counts["no_reply"] += 1
            if example_failure is None:
                example_failure = event

    duplicate_keys = {
        key: count
        for key, count in identity_counts.items()
        if count > 1
    }

    print(f"\n{'=' * 60}")
    print(f"Measurement {measurement_id}")
    print(f"{'=' * 60}")

    print(f"Total events: {len(results)}")
    print(f"Unique candidate identities: {len(identity_counts)}")
    print(f"Duplicate candidate identities: {len(duplicate_keys)}")
    print(f"Reply categories: {dict(reply_counts)}")

    print("\nTop-level fields:")
    for field, count in field_counts.most_common():
        print(f"  {field}: {count}")

    print("\nExample successful event:")
    print(json.dumps(example_success, indent=2)[:2000])

    print("\nExample event without RTT replies:")
    print(json.dumps(example_failure, indent=2)[:2000])

    if duplicate_keys:
        print("\nFirst five duplicate identities:")
        for key, count in list(duplicate_keys.items())[:5]:
            print(f"  {key}: {count} occurrences")


def main():
    for measurement_id in MEASUREMENT_IDS:
        analyze_measurement(measurement_id)


if __name__ == "__main__":
    main()
