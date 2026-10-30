
import asyncio

import pytest

from probenet.collectors.subscriber import read_messages


@pytest.mark.asyncio
async def test_bounded_queue_blocks_when_full():
    queue = asyncio.Queue(maxsize=2)

    await queue.put("event_1")
    await queue.put("event_2")

    assert queue.full()
    assert queue.qsize() == 2

    # Create a task that attempts to insert a third event.
    pending_put = asyncio.create_task(queue.put("event_3"))

    # Let the event loop give the pending task a chance to run.
    await asyncio.sleep(0)

    # The third event cannot enter a full queue.
    assert not pending_put.done()

    # The consumer removes one event.
    first_event = await queue.get()
    queue.task_done()

    assert first_event == "event_1"

    # Space is now available for the third event.
    await asyncio.wait_for(pending_put, timeout=1)

    assert queue.qsize() == 2
    assert await queue.get() == "event_2"
    queue.task_done()

    assert await queue.get() == "event_3"
    queue.task_done()

    await queue.join()
    assert queue.empty()


@pytest.mark.asyncio
async def test_queue_stays_bounded_with_slow_consumer():
    queue = asyncio.Queue(maxsize=3)
    processed = []
    maximum_observed_size = 0

    async def producer():
        nonlocal maximum_observed_size

        for number in range(10):
            await queue.put(number)
            maximum_observed_size = max(
                maximum_observed_size,
                queue.qsize(),
            )

    async def consumer():
        for _ in range(10):
            item = await queue.get()

            try:
                await asyncio.sleep(0.01)
                processed.append(item)
            finally:
                queue.task_done()

    await asyncio.wait_for(
        asyncio.gather(producer(), consumer()),
        timeout=5,
    )

    await queue.join()

    assert maximum_observed_size <= 3
    assert queue.empty()
    assert processed == list(range(10))


@pytest.mark.asyncio
async def test_subscriber_producer_respects_queue_limit():
    """Verify the actual subscriber blocks when its queue is full."""

    class FakeWebSocket:
        """Simulate a WebSocket that supplies five messages."""

        def __init__(self):
            self.messages = [f"event_{i}" for i in range(5)]

        def __aiter__(self):
            self.iterator = iter(self.messages)
            return self

        async def __anext__(self):
            try:
                return next(self.iterator)
            except StopIteration:
                raise StopAsyncIteration from None

    queue = asyncio.Queue(maxsize=2)
    websocket = FakeWebSocket()

    # Start the real subscriber producer.
    producer = asyncio.create_task(
        read_messages(websocket, queue)
    )

    # Allow it to fill the queue.
    await asyncio.sleep(0)

    assert queue.qsize() == 2
    assert not producer.done()

    received = []

    # Simulate a consumer processing messages.
    for _ in range(5):
        message, received_at = await asyncio.wait_for(
            queue.get(),
            timeout=1,
        )

        received.append(message)
        assert received_at.tzinfo is not None

        queue.task_done()
        await asyncio.sleep(0)

    # The producer should now finish.
    await asyncio.wait_for(producer, timeout=1)
    await queue.join()

    assert received == [f"event_{i}" for i in range(5)]
    assert queue.empty()
