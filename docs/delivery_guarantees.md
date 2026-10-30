# ProbeNet — Delivery Guarantees and Failure Semantics

## 1. Overview

ProbeNet collects real-time RIPE Atlas ping observations through WebSocket subscriptions.

The current collector uses an asynchronous producer-consumer pipeline with a bounded in-memory queue, payload validation, normalization, optional diagnostic capture, and structured logging.

The collector is designed for best-effort streaming ingestion. It does not currently guarantee lossless, exactly-once, or durable delivery.

## 2. Current Delivery Semantics

ProbeNet currently provides **best-effort, non-durable processing**.

- Messages are received through a WebSocket connection.
- The producer inserts incoming messages into an `asyncio.Queue`.
- The consumer validates and normalizes supported ping observations.
- Processed observations are emitted as structured logs.
- There is no durable event broker or transactional storage sink.
- There is no application-level acknowledgement or replay cursor for missed WebSocket messages.

A successful queue insertion does not mean the observation has been durably stored.

## 3. Failure Scenarios

| Scenario | Current behavior | Potential impact |
|---|---|---|
| Temporary connection failure | Reconnection with exponential backoff | Messages emitted while disconnected may be missed |
| Collector process crash | In-memory state and queued messages are lost | Unprocessed observations may be lost |
| Slow consumer | Bounded queue applies backpressure | Producer pauses when the queue fills; upstream buffering or delivery may be affected |
| Normal WebSocket closure | Pipeline attempts to drain queued messages before stopping its consumer | Existing queued messages are processed if draining completes |
| Producer exception or forced shutdown | Consumer task is cancelled during cleanup | Queued messages may remain unprocessed |
| Duplicate observations | No persistent deduplication during live collection | Duplicate observations may be processed more than once |
| Invalid payload | Validation error is logged and counted | Invalid observations are excluded from normalized output |

## 4. Event Identity and Deduplication

The project defines an observation identity using:

`(msm_id, prb_id, timestamp)`

Historical collision analysis found no duplicate identities among the 105,582 observations examined during M1.07.

This result supports the usefulness of the selected identity for the examined dataset. It does not establish universal uniqueness across all future RIPE Atlas observations.

The current live collector does not yet enforce persistent deduplication.

## 5. Backpressure

The WebSocket producer and message consumer communicate through a bounded `asyncio.Queue` with a maximum capacity of 1,000 messages.

When the queue reaches capacity, `await queue.put()` suspends the producer until space becomes available.

This prevents unlimited growth of the application-level queue.

It does not guarantee that upstream buffering is unlimited or that data cannot be lost during prolonged overload.

## 6. Reconnection

The collector uses exponential retry delays beginning at one second and capped at 30 seconds.

After a connection remains active for at least 60 seconds, the retry delay is reset to its initial value.

Reconnection restores streaming subscriptions but does not automatically retrieve observations missed while disconnected.

## 7. Raw Capture and Replay

ProbeNet supports optional bounded JSONL capture of raw WebSocket messages and their local receipt timestamps.

This is intended for debugging, reproduction, and short diagnostic sessions.

The feature is disabled by default.

Captured messages can be read back using the replay utility, but the current collector does not automatically replay them into the live processing pipeline.

Because capture is optional and limited, it is not a durable delivery mechanism.

## 8. Observability

The collector tracks:

- Messages received
- Valid ping observations processed
- Invalid messages
- Control messages
- Current queue occupancy
- Maximum observed queue occupancy
- Average processing throughput

Metrics are maintained in memory and reset when the collector process restarts.

They provide operational visibility but do not independently verify completeness against the upstream source.

## 9. M1.12 Smoke-Test Evidence

During a five-minute smoke test, the collector reported the following values at its final supplied periodic checkpoint, approximately 290.72 seconds after startup.

| Metric | Observed value |
|---|---:|
| Messages received | 53,218 |
| Ping observations processed | 53,215 |
| Control messages | 3 |
| Invalid messages | 0 |
| Maximum observed queue occupancy | 33 / 1,000 |
| Queue occupancy at checkpoint | 0 |
| Average processing throughput | 183.05 pings/second |

These results indicate that the consumer kept pace with the observed incoming traffic during the sampled interval.

They do not prove zero upstream message loss or long-term fault tolerance.

## 10. Future Improvements

Later milestones may introduce durable raw-event storage, replay-driven recovery, idempotent sink writes, persistent deduplication, and stronger operational monitoring.

Any stronger delivery guarantee must be established through actual implementation and fault-injection testing rather than assumed from the current design.

## 11. Conclusion

**ProbeNet M1 provides best-effort, non-durable streaming ingestion with bounded application-level buffering, automatic reconnection, optional diagnostic capture, and operational metrics.**

Exactly-once delivery, guaranteed recovery after downtime, and persistent durability are outside the current M1 implementation.
