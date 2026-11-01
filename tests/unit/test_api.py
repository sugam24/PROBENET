
"""Tests for ProbeNet's HTTP API."""

import pytest
from fastapi.testclient import TestClient

from probenet.api import main


@pytest.fixture
def client(monkeypatch):
    """Create an API client with controlled database responses."""

    def fake_execute_query(request, query, parameters=None):
        parameters = parameters or {}

        if "FROM dim_measurement" in query:
            if "WHERE measurement_id" in query:
                if parameters["measurement_id"] == 999999:
                    return []
                return [{"measurement_id": parameters["measurement_id"]}]

            return [
                {
                    "measurement_id": 1001,
                    "target": "k.root-servers.net",
                    "measurement_type": "ping",
                    "interval_seconds": 240,
                    "status": "Ongoing",
                    "is_public": True,
                }
            ]

        if "GROUP BY" in query:
            return [
                {
                    "measurement_id": 1001,
                    "hour_utc": "2026-11-01T10:00:00Z",
                    "observation_count": 2,
                    "observations_with_rtt": 1,
                    "unique_probes": 2,
                    "total_packets_sent": 6,
                    "total_packets_received": 3,
                    "total_packets_lost": 3,
                    "average_rtt_ms": 42.5,
                    "packet_loss_ratio": 0.5,
                }
            ]

        if "FROM fact_ping" in query:
            return [
                {
                    "measurement_id": 1001,
                    "probe_id": 62240,
                    "event_time": "2026-11-01T10:53:08Z",
                    "received_at": "2026-11-01T10:53:11Z",
                    "packets_sent": 3,
                    "packets_received": 0,
                    "loss_ratio": 1.0,
                    "average_rtt_ms": None,
                    "min_rtt_ms": None,
                    "max_rtt_ms": None,
                }
            ]

        raise AssertionError(f"Unexpected query: {query}")

    monkeypatch.setattr(main, "execute_query", fake_execute_query)
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_measurements(client):
    response = client.get("/measurements")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["measurement_id"] == 1001
    assert data[0]["target"] == "k.root-servers.net"


def test_hourly_metrics(client):
    response = client.get("/measurements/1001/hourly?limit=3")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["observation_count"] == 2
    assert data[0]["total_packets_lost"] == 3
    assert data[0]["packet_loss_ratio"] == 0.5
    assert data[0]["observations_with_rtt"] == 1


def test_recent_pings_preserve_null_rtt(client):
    response = client.get("/measurements/1001/pings?limit=5")

    assert response.status_code == 200

    ping = response.json()[0]

    assert ping["packets_sent"] == 3
    assert ping["packets_received"] == 0
    assert ping["loss_ratio"] == 1.0
    assert ping["average_rtt_ms"] is None
    assert ping["min_rtt_ms"] is None
    assert ping["max_rtt_ms"] is None


def test_unknown_measurement_returns_404(client):
    response = client.get("/measurements/999999/hourly")

    assert response.status_code == 404


@pytest.mark.parametrize("limit", [0, 169, -1])
def test_invalid_hourly_limit_returns_422(client, limit):
    response = client.get(
        "/measurements/1001/hourly",
        params={"limit": limit},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 501])
def test_invalid_ping_limit_returns_422(client, limit):
    response = client.get(
        "/measurements/1001/pings",
        params={"limit": limit},
    )

    assert response.status_code == 422
