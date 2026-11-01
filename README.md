# PROBENET

**Explore Internet latency, packet loss and data gaps using real RIPE Atlas measurements.**

PROBENET is being built as a globally capable network monitoring and analytics platform, with **Nepal as the initial implementation focus**. The goal is to make network observations useful—and show how much evidence supports each conclusion.

**Completed:** M0 feasibility + M1 streaming collector + M2 PostgreSQL-backed observability MVP · **Next:** M3 historical imports and gap reconciliation · **Full roadmap:** M0–M8

[Current progress](#current-progress) · [File guide](#file-guide) · [Getting started](#getting-started-and-running-probenet) · [Roadmap](#roadmap) · [Project references](#project-references)

## What will you be able to investigate?

- How did latency to a selected destination change during a given period?
- Did several independent probes observe packet loss, or only one?
- Which probes and networks contributed to the result?
- Is an apparent problem in the network—or is the collection pipeline missing data?

The current collector receives **global observations** from selected public measurements; it does not filter ingestion to Nepal. The current dashboard explores stored global observations by measurement. Nepal remains the initial analytical focus; country and ASN filters are future work, not current dashboard controls. Observations from a small probe cohort cannot establish national ISP rankings or country-wide outages.

## Current progress

| Area | What exists | Status |
| --- | --- | --- |
| Repository and tooling | uv package and lockfile, Ruff, pytest/pytest-asyncio, GitHub Actions workflow | Implemented |
| M0 feasibility | Probe discovery, three selected measurements and 105,582 historical observations | Completed; [source caveats](docs/feasibility.md) retained |
| Contracts and identity | Pydantic contracts, normalization, provisional event keys and SHA-256 fingerprints | Implemented and unit tested |
| Live collector and storage | Global multi-measurement subscriptions, bounded queue, reconnect backoff and idempotent PostgreSQL writes | M2 completed |
| Diagnostics and metrics | Optional JSONL capture/reader, storage-outcome counters and 10-second JSON metrics | Implemented; [results below](#collector-evidence-and-limits) |
| Delivery semantics | Persistent canonical records and conflict audit; best-effort capture before database commit | [M2 acceptance and limits](docs/m2_acceptance.md) |
| First usable product | PostgreSQL 17, SQL analytics, FastAPI and manually refreshed Streamlit dashboard | **M2 · Completed** |
| Historical recovery | Repeatable imports, interval state and gap reconciliation | **M3 · Next** |

M0, all 13 M1 tasks and all 12 M2 tasks are completed. The [M2 acceptance report](docs/m2_acceptance.md) records the working end-to-end product; the inspected implementation history reaches `3d49152`. Milestone completion does not establish complete source capture or exactly-once delivery. The [feasibility assessment](docs/feasibility.md) remains the earlier M0 snapshot and still lists evidence gaps; those caveats remain visible rather than being treated as resolved by this status update.

## File guide

Click a filename to inspect its implementation. All Python paths below are relative to `src/probenet/`.

### Collector, contracts and transformations

| File | What it does |
| --- | --- |
| [`collectors/subscriber.py`](src/probenet/collectors/subscriber.py) | Main runnable collector: loads measurement IDs, subscribes, queues, validates, normalizes and persists observations via `asyncio.to_thread()`; reconnects on handled connection failures and logs storage errors/conflicts. |
| [`collectors/raw_capture.py`](src/probenet/collectors/raw_capture.py) | `RawCaptureWriter` saves a bounded diagnostic JSONL sample; `replay_capture()` yields original messages and receipt timestamps. |
| [`collectors/metrics.py`](src/probenet/collectors/metrics.py) | In-memory received/processed/control/invalid counters, inserted/duplicate/conflict/storage-error outcomes, queue occupancy, uptime and average processing rate. |
| [`contracts/atlas.py`](src/probenet/contracts/atlas.py) | Source ping, packet and result-envelope models; validates identifiers and packet counts while accepting extra source fields. The subscriber checks frame shape directly and validates payloads with `AtlasPingResult`. |
| [`contracts/normalized.py`](src/probenet/contracts/normalized.py) | Internal ping model with event/receipt times, packet counts, nullable RTT and loss ratio. |
| [`contracts/identity.py`](src/probenet/contracts/identity.py) | Provisional `(msm_id, prb_id, timestamp)` key and deterministic SHA-256 of validated payload JSON; excludes `stored_timestamp`. |
| [`transforms/ping.py`](src/probenet/transforms/ping.py) | Converts source timestamps to UTC, computes loss ratio and maps missing/negative RTT aggregates to null. Zero sent packets produce null loss. |

The collector now uses these identities and fingerprints through the PostgreSQL repository: identical repeats leave one canonical observation; changed payloads for an existing identity are audited separately. Idempotent writes do not establish exactly-once source delivery.

### Storage, API and dashboard

| File | What it does |
| --- | --- |
| [`compose.yaml`](compose.yaml) | Runs PostgreSQL 17 under the `storage` profile, bound to `127.0.0.1:5434`, with a health check and persistent `postgres_data` named volume. |
| [`storage/database.py`](src/probenet/storage/database.py) | Loads the root `.env` and creates the SQLAlchemy/Psycopg engine for local database/user `probenet`. |
| [`storage/ping_repository.py`](src/probenet/storage/ping_repository.py) | Transactionally saves raw payloads and normalized facts; rolls back duplicate writes and records distinct conflicting payloads while preserving canonical data. |
| [`storage/load_metadata.py`](src/probenet/storage/load_metadata.py) | Manually fetches and upserts measurements 1001/1004/1005 and two fixed probe records. This is not scheduled refresh or a complete global probe catalog. |
| [`api/main.py`](src/probenet/api/main.py) | FastAPI metadata, hourly analytics, recent-observation and freshness/continuity endpoints using bound SQL parameters and response models. |
| [`dashboard/app.py`](src/probenet/dashboard/app.py) | Streamlit interface calling FastAPI: measurement selection, RTT/loss summaries, hourly charts/detail, recent pings and collection health. Refresh is manual. |
| [`hourly_ping_metrics.sql`](sql/analytics/hourly_ping_metrics.sql) | UTC event-hour/measurement aggregates: counts, valid RTT samples, distinct probes, sent/received/lost packets, mean observation RTT and packet-weighted loss. Null RTT is excluded from averages. |
| [`alembic.ini`](alembic.ini), [`migrations/env.py`](migrations/env.py) | Migration configuration and credential-aware database connection setup. |

<details>
<summary><strong>Schema migrations and persistence rules</strong></summary>

| Migration | Adds |
| --- | --- |
| [`e83825190032`](migrations/versions/e83825190032_create_raw_results_and_ping_facts.py) | `raw_results` with JSONB `payload`, `payload_hash`, event/receipt/persistence times; `fact_ping` with normalized metrics and packet/loss/address-family constraints. |
| [`83264759e687`](migrations/versions/83264759e687_create_probe_and_measurement_metadata_.py) | Current metadata tables `dim_probe` and `dim_measurement`. |
| [`027469e4edd6`](migrations/versions/027469e4edd6_add_canonical_ping_uniqueness.py) | Unique canonical identity `(measurement_id, probe_id, event_time)` and unique `raw_result_id` on `fact_ping`. |
| [`cab71a5070a6`](migrations/versions/cab71a5070a6_add_ping_conflict_audit_table.py) | `ping_conflicts`: incoming payload/hash linked to the canonical raw record; repeated identical conflicts share one audit row. |
| [`e4c4ea2cf8bb`](migrations/versions/e4c4ea2cf8bb_add_ping_measurement_time_index.py) | Composite B-tree index `ix_fact_ping_measurement_event_time` on `(measurement_id, event_time)`; current migration head. |

The repository preserves the first canonical observation when a later payload has the same logical identity and a different hash. Canonical raw/fact writes commit together; conflict audit uses a separate transaction after the canonical-write attempt rolls back.

</details>

### M0 discovery and learning utilities

| File | What it does | Inputs → outputs |
| --- | --- | --- |
| [`discovery/probes.py`](src/probenet/discovery/probes.py) | Fetches all pages of probe metadata; defaults to Nepal. Reports connection status and IPv4 ASN diversity. | Probe API → terminal inventory |
| [`discovery/measurements.py`](src/probenet/discovery/measurements.py) | Finds up to 10 candidate public, running ping measurements. | Measurement API → IDs, targets, intervals and status |
| [`discovery/inspect_measurements.py`](src/probenet/discovery/inspect_measurements.py) | Inspects settings for IDs **1001, 1004 and 1005**, including target, IP family, packets and interval. | Measurement details → terminal comparison fields |
| [`discovery/historical.py`](src/probenet/discovery/historical.py) | Downloads a ten-minute window ending ten minutes before execution for all three IDs. | Results API → `data/raw/measurement_<id>.json` |
| [`discovery/throughput.py`](src/probenet/discovery/throughput.py) | Samples stream 1001 for about 60 seconds and counts result messages and UTF-8 message bytes. | Live stream → event rate, byte rate and average size |
| [`discovery/analyze_payloads.py`](src/probenet/discovery/analyze_payloads.py) | Examines saved records for fields, RTT entries, no-reply examples and repeated candidate identities. | Three local JSON captures → terminal analysis |
| [`discovery/nepal_participation.py`](src/probenet/discovery/nepal_participation.py) | Checks which currently connected Nepal probes appear in each historical capture. | Current probe metadata + local captures → probe/ASN participation |
| [`collectors/atlas_stream.py`](src/probenet/collectors/atlas_stream.py) | Connects to stream 1001 and prints decoded frames until interrupted. Earlier learning utility; use `subscriber.py` for the current persisted collector. | WebSocket → terminal frames |
| [`__init__.py`](src/probenet/__init__.py) | Defines the `probenet` console entry point; currently prints a greeting. | `probenet` command → greeting |
| [`discovery/check_identity.py`](src/probenet/discovery/check_identity.py) | Validates saved observations and counts new keys, exact duplicates, conflicting hashes and rejections. | Local captures → identity audit |
| [`discovery/__init__.py`](src/probenet/discovery/__init__.py) | Empty package initializer for the discovery modules. | Package structure only |

### Configuration, documentation and data

| File or folder | Purpose | Current state |
| --- | --- | --- |
| [`pyproject.toml`](pyproject.toml) | Python version requirement, dependencies, development tools and package entry point | Main project configuration |
| [`uv.lock`](uv.lock) | Records resolved dependency versions for reproducible installation | Present |
| [`.python-version`](.python-version) | Selects the project’s Python version | Python 3.14 |
| [`.gitignore`](.gitignore) | Keeps environments, Python caches, `.env` and raw captures out of Git | Configured |
| [`requirements.txt`](requirements.txt) | Reserved from the initial skeleton; dependency declarations currently live in `pyproject.toml` | Empty |
| [`config/measurements.json`](config/measurements.json) | Selected global measurement subscriptions | IDs 1001, 1004 and 1005 |
| [`.env.example`](.env.example) | Older collector settings example; database credential setup is explained below | Missing `PROBENET_DB_PASSWORD`; some collector settings remain unused |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Python 3.14 setup, locked dependency sync, Ruff and pytest on main pushes/PRs | Workflow present; hosted run status not checked here |
| [`docs/event-identity.md`](docs/event-identity.md) | Key policy, payload canonicalization and historical collision analysis | M1.07 evidence |
| [`docs/delivery_guarantees.md`](docs/delivery_guarantees.md) | Historical M1 failure semantics and smoke-test results | Predates M2 persistence; read with current limits below |
| [`docs/m2_acceptance.md`](docs/m2_acceptance.md) | End-to-end PostgreSQL/API/dashboard acceptance and measured M2 results | Passed on 2026-11-01 |
| [`README.md`](README.md) | Project entry point, file guide and development tracker | You are here |
| [`docs/feasibility.md`](docs/feasibility.md) | Detailed M0 findings, evidence quality, limitations and outstanding checks | Maintained |
| [`docs/ProbeNet_Master_Build_Handbook_v1.1.docx`](docs/ProbeNet_Master_Build_Handbook_v1.1.docx) | Original project vision, architecture and milestone definitions | Reference; unchanged |
| `data/raw/measurement_{1001,1004,1005}.json` | Existing local historical captures used by the analysis scripts | Local only; ignored by Git |
| [`evidence/m0/`](evidence/m0/) | Intended home for dated M0 logs and small evidence artifacts | `.gitkeep` only |
| [`tests/fixtures/`](tests/fixtures/) | Representative ping inputs and deliberately modified edge cases | Four JSON fixtures; see below |
| `.gitkeep` files | Let Git track otherwise empty directories, including the original `docs/` skeleton | Placeholders |

### Fixtures and tests

| Files | Coverage |
| --- | --- |
| [`ping_success.json`](tests/fixtures/ping_success.json), [`ping_no_reply.json`](tests/fixtures/ping_no_reply.json) | Successful replies and a timeout with partial loss. Despite its name, `ping_no_reply.json` includes one successful reply. |
| [`ping_malformed.json`](tests/fixtures/ping_malformed.json), [`ping_extra_fields.json`](tests/fixtures/ping_extra_fields.json) | Deliberately invalid packet count and an added source field. |
| [`test_ping_normalization.py`](tests/unit/test_ping_normalization.py) | Success, partial/complete loss, zero sent, invalid counts, malformed input and extra fields. Complete loss is constructed in the test. |
| [`test_event_identity.py`](tests/unit/test_event_identity.py) | Stable keys/hashes, changed payloads, field ordering, storage-time exclusion and distinct probes. |
| [`test_subscriber.py`](tests/unit/test_subscriber.py), [`test_bounded_queue.py`](tests/unit/test_bounded_queue.py) | Configuration/subscription shape and bounded producer behavior with a slow consumer. |
| [`test_reconnection.py`](tests/unit/test_reconnection.py), [`test_pipeline_shutdown.py`](tests/unit/test_pipeline_shutdown.py) | Simulated retry/backoff/reset/cap/timeout behavior and queue draining on normal closure. |
| [`test_raw_capture.py`](tests/unit/test_raw_capture.py) | Capture/readback round trip and event limit. |
| [`test_api.py`](tests/unit/test_api.py) | Mocked database responses: health/metadata/analytics/pings, null RTT, unknown measurement, bounded limits and stale monitoring. |
| [`check_ping_storage.py`](tests/integration/check_ping_storage.py), [`check_ping_conflicts.py`](tests/integration/check_ping_conflicts.py) | Manual database checks for duplicate writes and distinct conflict auditing; write and clean up synthetic test rows, so they are not read-only checks. |
| [`test_packet_loss.py`](tests/unit/test_packet_loss.py) | Introductory percentage-calculation test; production loss ratios are tested in normalization tests. |

**Accepted M2 baseline on 2026-11-01:** Ruff passed; **37 tests passed**, with one Starlette/httpx deprecation warning, as recorded in the [acceptance report](docs/m2_acceptance.md). Unit tests use fixtures, simulated failures and mocked API database responses; the manual storage checks are separate from pytest discovery. These tests do not prove source completeness, sustained production reliability or recovery under every fault.

## Getting started and running ProbeNet

Use Python **3.14+**, `uv`, Docker with Compose, and Internet access for metadata/live collection. Run commands from the **local repository root** so configuration paths resolve. The complete local flow is RIPE Atlas → collector → PostgreSQL → FastAPI → Streamlit.

### One-time setup

Sync the locked dependencies:

```bash
uv sync --locked
```

Create `.env` if it does not already exist, then edit it locally:

```bash
if [ ! -e .env ]; then
  cp .env.example .env
fi
```

Add `PROBENET_DB_PASSWORD` with a strong private value to `.env`. The example currently omits this required setting. Compose, Alembic and the database helpers read the root `.env`; never commit it. Use the same password for the application and database. Compose initializes credentials on the first empty-volume startup; changing `.env` later does not change an existing database role's password.

| Setting | Current behavior |
| --- | --- |
| `PROBENET_DB_PASSWORD` | Required in local `.env` or the process environment; database/user `probenet`, host `127.0.0.1`, application port `5434`. |
| `PROBENET_API_URL` | Optional shell environment override for the dashboard; defaults to `http://127.0.0.1:8000`. The dashboard does not itself load `.env`. |
| `config/measurements.json` | Collector subscription IDs: 1001, 1004 and 1005. |
| `PROBENET_CAPTURE_*` | Optional diagnostic capture settings described below. |

Start storage, wait until it reports healthy, apply migrations and manually load metadata:

```bash
docker compose --profile storage up -d db
docker compose --profile storage ps
uv run alembic upgrade head
uv run python -m probenet.storage.load_metadata
```

The loader populates selected measurement metadata used by the API/dashboard, plus two fixed probe records. Targets are 1001 → `k.root-servers.net`, 1004 → `f.root-servers.net`, and 1005 → `i.root-servers.net`. Metadata refresh is manual. If the database already has these records and current migrations, repeat setup only when needed.

PostgreSQL stores data in a named Docker volume; stopping/removing the service container normally retains it. Container-recreation persistence is reported in the supplied development history. Avoid volume-removal commands if you want to retain observations.

### Run the application

Keep PostgreSQL running and use **three separate terminals**, each at the repository root:

**Terminal 1 — FastAPI:**

```bash
uv run uvicorn probenet.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Streamlit:**

```bash
uv run streamlit run src/probenet/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

**Terminal 3 — live collector:**

```bash
uv run python -m probenet.collectors.subscriber
```

Open [the dashboard](http://127.0.0.1:8501) or [interactive API documentation](http://127.0.0.1:8000/docs). PostgreSQL is local on port **5434**, FastAPI on **8000**, and Streamlit on **8501**. Use **Refresh Data** in the dashboard to reload stored observations and recalculate health. The API/dashboard can display historical stored data while the collector is stopped; charts alone do not establish continuous collection. The `probenet` console entry point still prints a greeting.

The collector subscribes to the three global measurements, validates/normalizes messages and persists observations via a worker thread. Structured metrics every **10 seconds** report received/processed messages, inserts, duplicates, conflicts, invalid inputs, storage errors, queue occupancy and throughput. Successful pings are no longer individually printed as normalized summaries.

The application queue holds at most **1,000 messages**; full queues suspend insertion. Handled connection failures use exponential retry delays from **1 to 30 seconds**, a **15-second** connection timeout and a delay reset after **60 seconds** connected. This bounds the application queue, not all upstream buffers. Cleanup stops the producer and attempts queue draining for up to **15 seconds** before cancelling the consumer. Normal-close draining and Ctrl+C were demonstrated; crashes and storage failures can still leave work unprocessed. Storage errors are counted and raised rather than treated as successful writes; guaranteed database-outage recovery is not implemented.

**Configuration boundary:** stream URL, queue size, retry settings and log level remain code constants. The corresponding older variables in `.env.example` do not override them. Unlike the M1 implementation, the database helper now loads `.env` before the collector connects; set capture options explicitly in the shell for a clear per-run configuration.

### Quality checks and shutdown

```bash
uv run ruff check src/ tests/
uv run pytest -q
```

Stop the collector with **Ctrl+C first**, keeping PostgreSQL available while queued writes drain. Then stop Streamlit and FastAPI with Ctrl+C. Finally stop storage without removing its volume:

```bash
docker compose --profile storage stop db
```

### API and dashboard behavior

| Endpoint | Behavior and limits |
| --- | --- |
| `GET /health` | Application liveness (`status: ok`); does not check database health or source completeness. |
| `GET /measurements` | Lists stored measurement metadata. Run the metadata loader before expecting selection options. |
| `GET /measurements/{measurement_id}/hourly` | Latest stored hourly aggregates; `limit` defaults to 24, range **1–168 groups**. |
| `GET /measurements/{measurement_id}/pings` | Latest persisted observations by event time; `limit` defaults to 50, range **1–500 rows**. |
| `GET /measurements/{measurement_id}/monitoring` | Latest stored receipt time/age, last-hour count and activity in **12 five-minute buckets**. |

Unknown measurement IDs return **404**; invalid limits return **422**. Query failures map to **503** for connection/operational errors or **500** for other database errors. SQL parameters are bound and responses validated. Row limits bound output; they do not enforce a scan-duration limit. Explicit start/stop, country, ASN and probe query filters are not implemented yet.

The dashboard requests up to **168 populated hourly groups** and **100 recent pings** for the selected measurement. Its RTT summary weights rounded hourly means by valid-RTT observation counts; packet loss uses total lost / total sent packets. A set of 168 stored hourly groups is not necessarily a continuous seven-day window. Charts, detail tables and health indicators refresh manually.

Freshness uses the latest **receipt timestamp**: fresh through 5 minutes, delayed above 5 through 15 minutes, and stale above 15 minutes, with separate no-data and clock-skew states (receipt more than 60 seconds ahead of the database clock). Continuity is active five-minute buckets / 12, not per-probe coverage or verified source completeness. The monitoring endpoint scans stored facts for a measurement; it is not a durable gap manifest.

<details>
<summary><strong>Enable a bounded diagnostic capture and read it back</strong></summary>

Choose a **new path** for each session; startup rejects an existing capture file. This example refuses an existing filename before launch:

```bash
if [ -e data/raw/example_capture.jsonl ]; then
  echo "Choose a new capture filename before running this example."
else
  PROBENET_CAPTURE_ENABLED=true \
  PROBENET_CAPTURE_PATH=data/raw/example_capture.jsonl \
  PROBENET_CAPTURE_MAX_EVENTS=100 \
  uv run python -m probenet.collectors.subscriber
fi
```

Capture is disabled by default. The limit counts raw WebSocket messages, including control messages. Reaching 100 stops capture writes, **not the collector**; use Ctrl+C when finished. Each JSONL entry preserves the message and its local receipt timestamp.

Count the saved entries:

```bash
wc -l data/raw/example_capture.jsonl
```

Read them using the existing Python replay interface, without printing raw addresses:

```bash
uv run python - <<'PYCODE'
from pathlib import Path
from probenet.collectors.raw_capture import replay_capture

count = 0
for raw_message, received_at in replay_capture(Path("data/raw/example_capture.jsonl")):
    count += 1
print(f"Read back {count} captured messages")
PYCODE
```

The capture example uses the current collector and therefore also requires migrated PostgreSQL storage and database credentials. Readback alone does not write to PostgreSQL, reinject messages into normalization or recover an outage automatically. Captures can include source/destination addresses and remain under ignored `data/raw/`; operational logs belong under ignored `data/logs/`.

</details>

<details>
<summary><strong>Run the retained M0 discovery experiments</strong></summary>

| Goal | Command | Needs |
| --- | --- | --- |
| Inspect saved payloads | `uv run python -m probenet.discovery.analyze_payloads` | Three local historical captures |
| Audit keys and hashes | `uv run python -m probenet.discovery.check_identity` | Three local historical captures |
| Count Nepal probes and ASNs | `uv run python -m probenet.discovery.probes` | Internet access |
| Discover public pings | `uv run python -m probenet.discovery.measurements` | Internet access |
| Inspect selected settings | `uv run python -m probenet.discovery.inspect_measurements` | Internet access |
| Sample stream 1001 volume | `uv run python -m probenet.discovery.throughput` | Internet access |
| Check Nepal participation | `uv run python -m probenet.discovery.nepal_participation` | Internet access + historical captures |

The historical downloader selects a new moving ten-minute window and **overwrites** the three fixed capture filenames. Preserve an existing dataset before running:

```bash
uv run python -m probenet.discovery.historical
```

The ignored historical captures are absent from a clean clone; checked-in fixtures are available for unit tests. Analysis output may contain addresses, so review it before publishing. Nepal participation uses current probe metadata and may differ from the original inventory.

</details>

## Collector evidence and limits

| Experiment | Observations | What it establishes |
| --- | --- | --- |
| M0 historical sample | 1001: 35,130; 1004: 35,236; 1005: 35,216. **105,582 total**, no repeated candidate keys. | Useful bounded history and sample-based identity evidence; not universal uniqueness. |
| M0 single-stream feasibility | Measurement 1001, about 60 seconds: **3,688 events**, 1,594,202 message bytes, **61.29 events/s**, **25.87 KiB/s**, about 432 bytes/event. | Original supplied source-volume baseline; separate from the M1 processing test. |
| M1 diagnostic capture | Supplied live check: **100 messages saved and 100 read back**. | Bounded diagnostic readback; not durable ingestion or automatic pipeline replay. |
| M1 multi-stream smoke test | Three measurements; final supplied periodic checkpoint at **290.72 seconds**: 53,218 messages, 53,215 processed pings, 3 controls, 0 invalid; queue 0, maximum **33/1,000**; **183.05 pings/s** average. | Consumer kept pace in the observed interval; counts reconcile as 53,218 = 53,215 + 3. Not a complete 300-second total or proof of zero upstream loss. |

The [M2 acceptance report](docs/m2_acceptance.md) records **182.5 seconds** of PostgreSQL-backed ingestion: **31,703 messages**, **31,700 processed pings**, **31,697 canonical inserts**, **3 audited conflicts**, **0 duplicates**, **0 invalid messages** and **0 storage errors**. Processing averaged **173.7 pings/s**; peak queue occupancy was **65/1,000** and final occupancy **0**. Accounting reconciled: 31,703 = 31,700 + 3 controls; 31,700 = 31,697 inserts + 3 conflicts. The run verified SQL/API/dashboard operation, stale-to-fresh transition and graceful shutdown. This is a bounded acceptance run, not a sustained production-load or lossless-source guarantee.

Supplied development evidence also records 13 hourly analytics groups with zero failed consistency groups. Individual local query plans measured **3.441 ms** with a sequential scan, **2.961 ms** with an indexed bitmap scan, and **1.616 ms** for a separate one-minute indexed query. These small-dataset observations are not a statistically validated or generalizable performance comparison.

The discovery-period Nepal inventory was **111 probes**: 71 abandoned, 17 written off, 16 connected, 5 disconnected and 2 never connected; the connected cohort represented **10 IPv4 ASNs**. These are historical observations, not permanent live counts or the size of the global ingestion stream.

**Current delivery boundary:** source ingestion is best effort; canonical observations and distinct conflict payloads are persisted once their database transactions commit. Identical writes are idempotent, not end-to-end exactly-once ingestion. There is no durable message broker, crash-surviving input queue, automated historical reconciliation or complete proof of source delivery. Metrics reset on restart; collector and dashboard are launched manually, and the dashboard refreshes manually. Stream warnings remain control-message logs/counters rather than completeness evidence. Database-outage recovery and sustained throughput remain unproven; source event timestamps later than receipt times also need investigation.

The [delivery-guarantees document](docs/delivery_guarantees.md) is an **M1 historical reference**: its statements about no persistent sink/deduplication predate M2 and no longer describe current database writes. Similarly, the [identity document](docs/event-identity.md) explains the key/hash policy but still describes M2 database behavior as future work. Use the repository and [M2 acceptance report](docs/m2_acceptance.md) for current behavior; neither historical document was changed here.

## Architecture at a glance

| Stage | Data flow | Availability |
| --- | --- | --- |
| Collector foundation · M1 | Configured global subscriptions → optional diagnostic capture → bounded asyncio queue → Pydantic validation and normalization | Implemented; extended by M2 persistence |
| First MVP · M2 | RIPE Atlas WebSocket → asynchronous collector → idempotent PostgreSQL writes/conflict audit → SQL analytics → FastAPI → Streamlit | **Implemented** |
| Historical recovery · M3 | Bounded REST history → shared contracts → idempotent storage + gap reconciliation | **Next** |
| Analytics and scheduling · M4–M5 | Canonical data → SQL/dbt models; Airflow coordinates bounded batch work | Planned |
| Full platform · M6 onward | Live collector → Kafka → validating consumer → ClickHouse; Parquet archives support rebuilds | Planned |

PostgreSQL currently stores canonical observations and metadata; in the longer-term architecture it remains the control plane for catalogs, intervals and job state. Live and historical paths must share event identity and metric definitions. Additional countries use the same platform; Nepal is the first cohort. Heavy infrastructure is introduced only after the earlier product gates work locally.

## Roadmap

Milestone names and ordering follow the handbook. Expand a milestone to see the working checklist. Related handbook tasks are grouped below by outcome so this page stays readable; their original task IDs are retained.

**Status:** Completed = milestone outcomes accepted in the supplied development history; Next = upcoming work; Planned = future implementation. Completed milestones retain their documented limitations. Checklist IDs follow the handbook; M1 and M2 are expanded to show each completed task.

| Milestone | Outcome | Status |
| --- | --- | --- |
| [M0](#m0) | Verify the data and freeze a realistic scope | **Completed** |
| [M1](#m1) | Set up the repository, data contract and live collector | **Completed** |
| [M2](#m2) | Deliver the first complete working product | **Completed** |
| [M3](#m3) | Make historical imports repeatable and reconcile gaps | **Next** |
| [M4](#m4) | Build the analytics engineering layer using SQL and dbt | Planned |
| [M5](#m5) | Orchestrate the batch pipeline with Airflow | Planned |
| [M6](#m6) | Upgrade to Kafka, ClickHouse and Parquet | Planned |
| [M7](#m7) | Make ProbeNet useful, measurable and resilient | Planned |
| [M8](#m8) | Package, document and demonstrate the complete project | Planned |

<a id="m0"></a>
<details>
<summary><strong>M0 · Verify the data and freeze a realistic scope — Completed</strong></summary>

- [x] **M0.01–M0.03:** Investigate source documentation, public streaming access and regional probe coverage.
- [x] **M0.04–M0.07:** Select and compare measurements; obtain bounded history and measure initial live volume.
- [x] **M0.08–M0.09:** Examine payload shapes and test a provisional identity on 105,582 historical observations.
- [x] **M0.10–M0.12:** Establish global-capable, Nepal-first analytical scope and a proceed verdict.

**Evidence:** [feasibility assessment](docs/feasibility.md), [measurement configuration](config/measurements.json) and [identity audit](docs/event-identity.md). Completion is reported in the supplied development history. The older feasibility document still lists unresolved evidence/acceptance items; dated neighboring-country metadata and `docs/product-scope.md` were not found during this README review. Those documentation gaps and source limitations remain explicit.

</details>

<a id="m1"></a>
<details>
<summary><strong>M1 · Set up the repository, data contract and live collector — Completed</strong></summary>

- [x] **M1.01:** Establish the src-layout Python package, uv configuration and lockfile.
- [x] **M1.02:** Configure Ruff, pytest/pytest-asyncio and [GitHub Actions](.github/workflows/ci.yml).
- [x] **M1.03:** Add example environment settings and [measurement subscription configuration](config/measurements.json); runtime support is described above.
- [x] **M1.04:** Save [success, loss, malformed and unexpected-field fixtures](tests/fixtures/).
- [x] **M1.05:** Define typed source and normalized ping contracts.
- [x] **M1.06:** Implement normalization with nullable RTT and packet-loss handling, covered by [unit tests](tests/unit/test_ping_normalization.py).
- [x] **M1.07:** Implement provisional event identity, canonical payload hashing and historical collision analysis; test key/hash behavior.
- [x] **M1.08:** Build the [configured multi-measurement subscriber](src/probenet/collectors/subscriber.py) with structured JSON logging.
- [x] **M1.09:** Bound the application queue to 1,000 messages and test producer backpressure.
- [x] **M1.10:** Add tested reconnect backoff, connection timeout and normal-close queue draining with interruption cleanup.
- [x] **M1.11:** Add bounded optional JSONL capture and a timestamp-preserving readback utility.
- [x] **M1.12:** Add in-memory counters, periodic queue/throughput metrics and supplied sustained smoke-test evidence.
- [x] **M1.13:** Document [delivery guarantees and failure semantics](docs/delivery_guarantees.md).

**M1 outcome:** a tested CLI streaming foundation with best-effort, non-durable processing at that stage. M2 now adds persistent canonical records and database deduplication; the historical M1 checklist is retained.

</details>

<a id="m2"></a>
<details>
<summary><strong>M2 · Deliver the first complete working product — Completed</strong></summary>

- [x] **M2.01:** Add PostgreSQL 17 in the Compose storage profile with local binding and persistent volume.
- [x] **M2.02:** Introduce SQLAlchemy/Psycopg and reproducible Alembic raw/fact schema migrations.
- [x] **M2.03:** Create probe/measurement metadata tables and a manual upsert loader.
- [x] **M2.04:** Enforce canonical event uniqueness and idempotent raw/fact writes.
- [x] **M2.05:** Preserve canonical records and audit distinct same-key/different-hash payloads.
- [x] **M2.06:** Persist validated live observations through `asyncio.to_thread()` with storage-outcome metrics and controlled shutdown.
- [x] **M2.07:** Add hourly counts, mean valid RTT and packet-weighted loss SQL; check aggregate consistency.
- [x] **M2.08:** Add the measurement/event-time index and record local query-plan evidence.
- [x] **M2.09:** Implement parameter-bound FastAPI metadata, hourly and recent-ping endpoints with validated limits/responses.
- [x] **M2.10:** Build the API-backed Streamlit measurement dashboard, charts and observation tables.
- [x] **M2.11:** Expose receipt-time freshness and five-minute collection-continuity indicators.
- [x] **M2.12:** Accept the real source → PostgreSQL → API → dashboard flow, including shutdown and measured counters.

**Outcome:** a working PostgreSQL-backed observability MVP. [M2 acceptance passed on 2026-11-01](docs/m2_acceptance.md), at migration head `e4c4ea2cf8bb`, with 37 passing tests. Crash-safe capture, automated recovery and full source completeness are not claimed.

</details>

<a id="m3"></a>
<details open>
<summary><strong>M3 · Make historical imports repeatable and reconcile gaps — Next</strong></summary>

- [ ] **M3.01–M3.03:** Build bounded incremental retrieval with shared validation and rate-limit-aware retries.
- [ ] **M3.04–M3.06:** Track interval states, resumable chunks, overlap, counts and source metadata.
- [ ] **M3.07–M3.10:** Prove safe reruns/restarts and reconcile a suspected live gap.
- [ ] **M3.11–M3.12:** Expose a manual backfill command and explain verified versus unresolved history.

**Done when:** rerunning a window preserves canonical counts and unresolved gaps remain visible.

</details>

<a id="m4"></a>
<details>
<summary><strong>M4 · Build the analytics engineering layer using SQL and dbt</strong></summary>

- [ ] **M4.01–M4.05:** Define reporting questions, lineage, grains, dimensions and justified metadata versioning.
- [ ] **M4.06–M4.09:** Build dbt staging, canonical facts/dimensions and hourly/daily aggregates.
- [ ] **M4.10–M4.12:** Test quality/freshness and recompute affected windows after late imports.
- [ ] **M4.13–M4.15:** Document models and verify outputs against independent reference SQL.

**Done when:** documented bronze/silver/gold models produce tested, replay-safe analytical results.

</details>

<a id="m5"></a>
<details>
<summary><strong>M5 · Orchestrate the batch pipeline with Airflow</strong></summary>

- [ ] **M5.01–M5.03:** Test standalone batch commands, then add a resource-limited interval DAG.
- [ ] **M5.04–M5.06:** Schedule metadata refresh, bounded imports, dbt transformations and quality gates.
- [ ] **M5.07–M5.10:** Demonstrate backfills, retries and safe reruns with logs and reconciliation evidence.

**Done when:** bounded batch workflows are scheduled, auditable and retry-safe.

</details>

<a id="m6"></a>
<details>
<summary><strong>M6 · Upgrade to Kafka, ClickHouse and Parquet</strong></summary>

- [ ] **M6.01–M6.05:** Baseline PostgreSQL, plan migration and publish acknowledged events to Kafka.
- [ ] **M6.06–M6.09:** Build a validating consumer, quarantine failures and prove crash/replay correctness for shared live/batch envelopes.
- [ ] **M6.10–M6.14:** Add verified ClickHouse reads, bounded Parquet archives and a tested rebuild path.
- [ ] **M6.15–M6.17:** Measure lag/resources, bound retention and demonstrate retained-message replay.

**Done when:** the dual-pipeline platform has correct analytical serving and demonstrated replay/archive recovery.

</details>

<a id="m7"></a>
<details>
<summary><strong>M7 · Make ProbeNet useful, measurable and resilient</strong></summary>

- [ ] **M7.01–M7.03:** Add investigation filters, geographic coverage and clearly defined probe metrics.
- [ ] **M7.04–M7.07:** Build baseline/anomaly evidence views; add DNS/traceroute only if coverage justifies them.
- [ ] **M7.08–M7.12:** Instrument pipeline health and test schema, network, database and replay failures.
- [ ] **M7.13–M7.17:** Benchmark ingestion/queries, verify aggregate invariants and document runbooks and correctness limits.

**Done when:** a useful network investigation and the platform’s tested failure behavior can both be demonstrated.

</details>

<a id="m8"></a>
<details>
<summary><strong>M8 · Package, document and demonstrate the complete project</strong></summary>

- [ ] **M8.01–M8.05:** Publish actual architecture, source constraints and a reproducible clean-start setup.
- [ ] **M8.06–M8.09:** Pass CI and capture screenshots, architecture decisions and measured benchmarks.
- [ ] **M8.10–M8.13:** Record product/recovery demonstrations, finish portfolio documentation and tag an accepted release.

**Done when:** a new reviewer can reproduce the project and verify its claims.

</details>

## Project references

| Reference | Use it for |
| --- | --- |
| [Master Build Handbook v1.1](docs/ProbeNet_Master_Build_Handbook_v1.1.docx) | Full vision, architecture, original task definitions and acceptance criteria |
| [M0 feasibility assessment](docs/feasibility.md) | Experiment counts, provenance, constraints, decisions and remaining evidence |
| [M2 acceptance](docs/m2_acceptance.md) | Current end-to-end verification, measured counters and remaining limitations |
| [Delivery guarantees · M1](docs/delivery_guarantees.md) | Historical pre-persistence semantics and M1 smoke-test evidence |
| [Event identity](docs/event-identity.md) | Provisional keys, hashing rules and historical validation |
| `docs/product-scope.md` · not present | Dedicated scope document referenced by the handbook; documentation gap retained |

Maintain this README as the project changes: update file purposes, statuses and milestone outcomes when evidence supports them. Detailed logs belong in `evidence/m0/`; experimental analysis belongs in the feasibility assessment. The handbook stays the roadmap reference.
