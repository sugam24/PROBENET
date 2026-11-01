
import asyncio
import json
from contextlib import asynccontextmanager

import pytest

from probenet.collectors import subscriber


@pytest.mark.asyncio
async def test_collector_reconnects_after_connection_failure(monkeypatch):
    attempts = 0
    subscriptions = []
    delays = []

    class FakeWebSocket:
        async def send(self, message):
            subscriptions.append(json.loads(message))

    @asynccontextmanager
    async def fake_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise OSError("Simulated connection failure")

        yield FakeWebSocket()

    async def fake_run_pipeline(
    websocket,
    queue,
    capture_writer=None,
    metrics=None,
    engine=None,
    ):
        # End the test after successful reconnection.
        raise asyncio.CancelledError()

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(subscriber, "connect", fake_connect)
    monkeypatch.setattr(subscriber, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(subscriber.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(subscriber.collect(), timeout=2)

    assert attempts == 2
    assert delays == [1]

    assert len(subscriptions) == 3
    assert [
        subscription[1]["msm"]
        for subscription in subscriptions
    ] == [1001, 1004, 1005]

    assert all(
        subscription[0] == "atlas_subscribe"
        for subscription in subscriptions
    )


@pytest.mark.asyncio
async def test_exponential_backoff_after_repeated_failures(monkeypatch):
    attempts = 0
    delays = []

    @asynccontextmanager
    async def fake_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1

        if attempts <= 3:
            raise OSError("Simulated connection failure")

        # End after the fourth connection attempt.
        raise asyncio.CancelledError()

        yield  # Makes this an asynchronous generator.

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(subscriber, "connect", fake_connect)
    monkeypatch.setattr(subscriber.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(subscriber.collect(), timeout=2)

    assert attempts == 4
    assert delays == [1, 2, 4]


@pytest.mark.asyncio
async def test_backoff_resets_after_stable_connection(monkeypatch):
    attempts = 0
    delays = []

    # Simulated monotonic time in seconds.
    current_time = [0.0]

    @asynccontextmanager
    async def fake_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1

        if attempts <= 2:
            raise OSError("Simulated connection failure")

        if attempts == 3:

            class FakeWebSocket:
                async def send(self, message):
                    pass

            yield FakeWebSocket()
            return

        raise asyncio.CancelledError()

        yield

    async def fake_run_pipeline(
    websocket,
    queue,
    capture_writer=None,
    metrics=None,
    engine=None,
    ):
        # Pretend the connection stayed healthy for 65 seconds.
        current_time[0] += 65

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(subscriber, "connect", fake_connect)
    monkeypatch.setattr(subscriber, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(subscriber.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        subscriber,
        "monotonic",
        lambda: current_time[0],
    )

    with pytest.raises(asyncio.CancelledError):
        await subscriber.collect()

    assert attempts == 4

    # Two failures increase the delay from 1 to 2.
    # A stable connection resets it to 1.
    assert delays == [1, 2, 1]


@pytest.mark.asyncio
async def test_backoff_never_exceeds_maximum(monkeypatch):
    attempts = 0
    delays = []

    @asynccontextmanager
    async def fake_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1

        if attempts <= 8:
            raise OSError("Simulated connection failure")

        raise asyncio.CancelledError()
        yield

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(subscriber, "connect", fake_connect)
    monkeypatch.setattr(subscriber.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await subscriber.collect()

    assert delays == [1, 2, 4, 8, 16, 30, 30, 30]


@pytest.mark.asyncio
async def test_connection_timeout_is_retried(monkeypatch):
    attempts = 0

    @asynccontextmanager
    async def fake_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise TimeoutError("Connection timed out")

        raise asyncio.CancelledError()
        yield

    async def fake_sleep(delay):
        assert delay == 1

    monkeypatch.setattr(subscriber, "connect", fake_connect)
    monkeypatch.setattr(subscriber.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await subscriber.collect()

    assert attempts == 2
