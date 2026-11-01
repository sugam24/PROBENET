
# ProbeNet M2 — End-to-End Acceptance Report

**Date:** 2026-11-01
**Status:** Passed
**Milestones:** M2.01–M2.12

## Architecture Verified

RIPE Atlas WebSocket
→ Async Collector
→ Validation and Normalization
→ PostgreSQL
→ FastAPI
→ Streamlit Dashboard

## Live Collector Results

| Metric | Result |
|---|---:|
| Duration | 182.5 seconds |
| Messages received | 31,703 |
| Pings processed | 31,700 |
| Canonical pings inserted | 31,697 |
| Duplicate pings | 0 |
| Payload conflicts | 3 |
| Invalid messages | 0 |
| Storage errors | 0 |
| Processing throughput | 173.7 pings/sec |
| Maximum queue occupancy | 65 |
| Final queue occupancy | 0 |

## Database Verification

PostgreSQL successfully persisted observations for
measurements 1001, 1004, and 1005.

Conflict detection was exercised by three incoming
observations with conflicting payloads.

Latest Alembic revision:
`e4c4ea2cf8bb (head)`

## API and Dashboard Verification

- Measurement metadata API: Passed
- Hourly analytics API: Passed
- Recent ping observations API: Passed
- Monitoring API: Passed
- Streamlit dashboard: Rendered successfully
- Freshness transition from stale to fresh: Verified
- Recent observation count increased during ingestion
- Collection continuity monitoring: Verified

## Code Quality

- Ruff: Passed
- Pytest: 37 passed
- One non-blocking Starlette/httpx deprecation warning

## Known Limitations

- The collector runs manually and does not yet provide
  continuous unattended operation.
- In-memory queued events cannot survive process crashes.
- Graceful shutdown was verified for this run, not every
  possible failure scenario.
- Dashboard refresh is manual.
- Five-minute activity buckets are a collection-continuity
  proxy, not an exact measure of participating-probe coverage.
- A few source event timestamps appear later than receipt
  timestamps and require further investigation.
- Sustained throughput and recovery under database outages
  have not yet been established.

## Acceptance Decision

M2 functional acceptance passed.

The system successfully ingested real RIPE Atlas observations,
persisted them in PostgreSQL, exposed analytical results
through FastAPI, and visualized them in Streamlit.

Remaining reliability and operational limitations are
documented for future milestones.
