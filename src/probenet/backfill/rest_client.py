
"""Bounded RIPE Atlas historical results client (M3.01)."""

import argparse
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE_URL = "https://atlas.ripe.net/api/v2"
MAX_WINDOW_SECONDS = 15 * 60
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp with an explicit UTC offset."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")

    return dt.astimezone(timezone.utc)


def build_results_url(
    measurement_id: int,
    start: datetime,
    stop: datetime,
    probe_ids: list[int] | None = None,
) -> str:
    """Validate a bounded interval and build its REST URL."""
    if measurement_id <= 0:
        raise ValueError("Measurement ID must be positive.")

    if start.tzinfo is None or stop.tzinfo is None:
        raise ValueError("Start and stop must be timezone-aware.")

    seconds = (stop - start).total_seconds()

    if not 0 < seconds <= MAX_WINDOW_SECONDS:
        raise ValueError(
            "Interval must be greater than zero "
            "and no longer than 15 minutes."
        )

    if stop > datetime.now(timezone.utc):
        raise ValueError("Historical stop time cannot be in the future.")

    if probe_ids is not None and any(pid <= 0 for pid in probe_ids):
        raise ValueError("Probe IDs must be positive.")

    params = {
        "start": int(start.timestamp()),
        "stop": int(stop.timestamp()),
        "format": "json",
    }

    if probe_ids:
        params["probe_ids"] = ",".join(map(str, probe_ids))

    return (
        f"{API_BASE_URL}/measurements/{measurement_id}/results/"
        f"?{urlencode(params)}"
    )


def fetch_results(url: str) -> list[dict]:
    """Fetch a small bounded response.

    Retries and incremental parsing are introduced in M3.02/M3.03.
    """
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ProbeNet-Learning/0.1",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)

    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError(
            "Response exceeds the 16 MiB safety limit. "
            "Use a smaller interval or probe filter."
        )

    results = json.loads(payload)

    if not isinstance(results, list):
        raise ValueError("Expected a JSON array of measurement results.")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a bounded RIPE Atlas historical interval."
    )
    parser.add_argument("--measurement", type=int, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--stop", required=True)
    parser.add_argument(
        "--probe-id",
        type=int,
        action="append",
        dest="probe_ids",
        help="Optional probe filter; may be repeated.",
    )

    args = parser.parse_args()

    try:
        start = parse_utc(args.start)
        stop = parse_utc(args.stop)

        url = build_results_url(
            measurement_id=args.measurement,
            start=start,
            stop=stop,
            probe_ids=args.probe_ids,
        )

        print(f"Request: {url}")

        results = fetch_results(url)

        print(f"Measurement: {args.measurement}")
        print(f"Start UTC: {start.isoformat()}")
        print(f"Stop UTC: {stop.isoformat()}")
        print(f"Fetched results: {len(results)}")

        if results:
            sample = results[0]
            print("First result summary:")
            print(
                json.dumps(
                    {
                        "msm_id": sample.get("msm_id"),
                        "prb_id": sample.get("prb_id"),
                        "timestamp": sample.get("timestamp"),
                        "type": sample.get("type"),
                    },
                    indent=2,
                )
            )

    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(status=1, message=f"Backfill request failed: {exc}\n")


if __name__ == "__main__":
    main()
