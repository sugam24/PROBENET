
import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_URL = "https://atlas.ripe.net/api/v2"

MEASUREMENT_IDS = [1001, 1004, 1005]
PROBE_IDS = [7475, 7670]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def get_engine():
    password = os.environ["PROBENET_DB_PASSWORD"]

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username="probenet",
        password=password,
        host="127.0.0.1",
        port=5434,
        database="probenet",
    )

    return create_engine(database_url)


async def fetch_metadata(client, endpoint, identifier):
    response = await client.get(
        f"{BASE_URL}/{endpoint}/{identifier}/"
    )
    response.raise_for_status()
    return response.json()


async def main():
    engine = get_engine()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with engine.begin() as connection:
                for measurement_id in MEASUREMENT_IDS:
                    metadata = await fetch_metadata(
                        client, "measurements", measurement_id
                    )

                    status = metadata.get("status") or {}

                    connection.execute(
                        text("""
                            INSERT INTO dim_measurement (
                                measurement_id,
                                target,
                                measurement_type,
                                interval_seconds,
                                status,
                                is_public
                            )
                            VALUES (
                                :measurement_id,
                                :target,
                                :measurement_type,
                                :interval_seconds,
                                :status,
                                :is_public
                            )
                            ON CONFLICT (measurement_id)
                            DO UPDATE SET
                                target = EXCLUDED.target,
                                measurement_type = EXCLUDED.measurement_type,
                                interval_seconds = EXCLUDED.interval_seconds,
                                status = EXCLUDED.status,
                                is_public = EXCLUDED.is_public,
                                metadata_updated_at = NOW()
                        """),
                        {
                            "measurement_id": metadata["id"],
                            "target": metadata.get("target"),
                            "measurement_type": metadata["type"],
                            "interval_seconds": metadata.get("interval"),
                            "status": status.get("name"),
                            "is_public": metadata.get("is_public"),
                        },
                    )

                    print(f"Loaded measurement {measurement_id}")

                for probe_id in PROBE_IDS:
                    metadata = await fetch_metadata(
                        client, "probes", probe_id
                    )

                    status = metadata.get("status") or {}

                    connection.execute(
                        text("""
                            INSERT INTO dim_probe (
                                probe_id,
                                country_code,
                                asn_v4,
                                status
                            )
                            VALUES (
                                :probe_id,
                                :country_code,
                                :asn_v4,
                                :status
                            )
                            ON CONFLICT (probe_id)
                            DO UPDATE SET
                                country_code = EXCLUDED.country_code,
                                asn_v4 = EXCLUDED.asn_v4,
                                status = EXCLUDED.status,
                                metadata_updated_at = NOW()
                        """),
                        {
                            "probe_id": metadata["id"],
                            "country_code": metadata.get("country_code"),
                            "asn_v4": metadata.get("asn_v4"),
                            "status": status.get("name"),
                        },
                    )

                    print(f"Loaded probe {probe_id}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
