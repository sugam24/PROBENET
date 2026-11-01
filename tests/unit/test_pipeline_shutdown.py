
import asyncio
import json

import pytest

from probenet.collectors.subscriber import run_pipeline


@pytest.mark.asyncio
async def test_pipeline_finishes_after_websocket_closes(monkeypatch):
    """Verify queued messages drain after a normal WebSocket close."""

    class FakeWebSocket:
        def __init__(self):
            self.messages = [
                json.dumps(["atlas_subscribed", {"msm": 1001}]),
                json.dumps(["atlas_subscribed", {"msm": 1004}]),
                json.dumps(["atlas_subscribed", {"msm": 1005}]),
            ]

        def __aiter__(self):
            self.iterator = iter(self.messages)
            return self

        async def __anext__(self):
            try:
                return next(self.iterator)
            except StopIteration:
                raise StopAsyncIteration from None

    processed = []

    async def fake_process_messages(queue, metrics=None, engine=None):
        while True:
            message, received_at = await queue.get()

            try:
                await asyncio.sleep(0.01)
                processed.append(json.loads(message)[0])
                assert received_at.tzinfo is not None
            finally:
                queue.task_done()

    # Replace the real consumer only for this test.
    monkeypatch.setattr(
        "probenet.collectors.subscriber.process_messages",
        fake_process_messages,
    )

    websocket = FakeWebSocket()
    queue = asyncio.Queue(maxsize=2)

    # If shutdown hangs, the test fails after one second.
    await asyncio.wait_for(
        run_pipeline(websocket, queue),
        timeout=1,
    )

    assert processed == [
        "atlas_subscribed",
        "atlas_subscribed",
        "atlas_subscribed",
    ]

    assert queue.empty()
