
"""Bounded and incremental RIPE Atlas historical results client."""

import argparse
import json
from collections.abc import Iterator
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from probenet.backfill.http_retry import open_with_retries
from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.normalized import NormalizedPing
from probenet.transforms.ping import normalize_ping

API_BASE_URL = "https://atlas.ripe.net/api/v2"

MAX_WINDOW_SECONDS = 15 * 60
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp with an explicit timezone."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")

    return dt.astimezone(timezone.utc)


def build_results_url(
    measurement_id: int,
    start: datetime,
    stop: datetime,
    probe_ids: list[int] | None = None,
    response_format: str = "json",
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

    if response_format not in {"json", "txt"}:
        raise ValueError("Unsupported response format.")

    params = {
        "start": int(start.timestamp()),
        "stop": int(stop.timestamp()),
        "format": response_format,
    }

    if probe_ids:
        params["probe_ids"] = ",".join(map(str, probe_ids))

    return (
        f"{API_BASE_URL}/measurements/{measurement_id}/results/"
        f"?{urlencode(params)}"
    )


def fetch_results(url: str) -> list[dict]:
    """Fetch a small bounded JSON-array response with HTTP retries."""
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ProbeNet-Learning/0.1",
        },
    )

    with open_with_retries(
        request,
        opener=urlopen,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
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


def stream_results(
    url: str,
) -> Iterator[tuple[AtlasPingResult, NormalizedPing]]:
    """Incrementally validate and normalize historical JSONL results.

    Each yielded item contains the validated source observation
    and its canonical normalized representation.

    Invalid records and incomplete responses cause explicit failures.
    """
    request = Request(
        url,
        headers={
            "Accept": "application/json, text/plain",
            "User-Agent": "ProbeNet-Learning/0.1",
        },
    )

    bytes_read = 0
    line_number = 0

    with open_with_retries(
        request,
        opener=urlopen,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        while True:
            raw_line = response.readline(MAX_LINE_BYTES + 1)

            if not raw_line:
                break

            line_number += 1
            bytes_read += len(raw_line)

            if len(raw_line) > MAX_LINE_BYTES:
                raise ValueError(
                    f"Line {line_number} exceeds the 1 MiB limit."
                )

            if bytes_read > MAX_RESPONSE_BYTES:
                raise ValueError(
                    "Historical response exceeds the 16 MiB "
                    "safety limit. Request a smaller interval."
                )

            try:
                payload = json.loads(raw_line)
            except (ValueError, UnicodeError) as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}"
                ) from exc

            if not isinstance(payload, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number}"
                )

            try:
                source = AtlasPingResult.model_validate(payload)

                # Historical retrieval time, not original source receipt.
                received_at = datetime.now(timezone.utc)

                normalized = normalize_ping(
                    source,
                    received_at,
                )

            except ValueError as exc:
                raise ValueError(
                    f"Invalid ping on line {line_number}: {exc}"
                ) from exc

            yield source, normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream a bounded RIPE Atlas historical interval."
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
            response_format="txt",
        )

        print(f"Request: {url}")
        print(f"Measurement: {args.measurement}")
        print(f"Start UTC: {start.isoformat()}")
        print(f"Stop UTC: {stop.isoformat()}")

        count = 0
        first_source = None
        first_normalized = None

        for source, normalized in stream_results(url):
            count += 1

            if first_source is None:
                first_source = source
                first_normalized = normalized

        print(f"Validated historical pings: {count}")

        if first_source is not None:
            print("First validated source:")
            print(
                json.dumps(
                    {
                        "msm_id": first_source.msm_id,
                        "prb_id": first_source.prb_id,
                        "timestamp": first_source.timestamp,
                        "type": first_source.type,
                    },
                    indent=2,
                )
            )

        if first_normalized is not None:
            print("First normalized ping:")
            print(
                first_normalized.model_dump_json(indent=2)
            )

    except (
        ValueError,
        OSError,
        UnicodeError,
        RuntimeError,
    ) as exc:
        parser.exit(
            status=1,
            message=f"Historical retrieval failed: {exc}\n",
        )


if __name__ == "__main__":
    main()
