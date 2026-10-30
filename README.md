# PROBENET

**Explore Internet latency, packet loss and data gaps using real RIPE Atlas measurements.**

PROBENET is being built as a globally capable network monitoring and analytics platform, with **Nepal as the initial implementation focus**. The goal is to make network observations useful—and show how much evidence supports each conclusion.

**Completed:** M0 feasibility + M1 streaming collector · **Next:** M2 PostgreSQL, API and dashboard · **Full roadmap:** M0–M8

[Current progress](#current-progress) · [File guide](#file-guide) · [Getting started](#getting-started-and-running-probenet) · [Roadmap](#roadmap) · [Project references](#project-references)

## What will you be able to investigate?

- How did latency to a selected destination change during a given period?
- Did several independent probes observe packet loss, or only one?
- Which probes and networks contributed to the result?
- Is an apparent problem in the network—or is the collection pipeline missing data?

The current collector receives **global observations** from selected public measurements; it does not filter ingestion to Nepal. The first dashboard will focus on participating Nepal probes and curated IPv4 ping measurements. Country and ASN filters will be configurable so the platform can expand to other regions. Observations from a small probe cohort cannot establish national ISP rankings or country-wide outages.

## Current progress

| Area | What exists | Status |
| --- | --- | --- |
| Repository and tooling | uv package and lockfile, Ruff, pytest/pytest-asyncio, GitHub Actions workflow | Implemented |
| M0 feasibility | Probe discovery, three selected measurements and 105,582 historical observations | Completed; [source caveats](docs/feasibility.md) retained |
| Contracts and identity | Pydantic contracts, normalization, provisional event keys and SHA-256 fingerprints | Implemented and unit tested |
| Live collector | Configured multi-measurement subscriptions, bounded queue and reconnect backoff | M1 completed |
| Diagnostics and metrics | Optional JSONL capture/reader, 10-second JSON metrics and supplied smoke-test evidence | Implemented; [results below](#collector-evidence-and-limits) |
| Delivery semantics | Best-effort, non-durable processing with documented failure behavior | [Documented](docs/delivery_guarantees.md) |
| First usable product | PostgreSQL persistence, bounded API and dashboard | **M2 · Next** |

M0 and all 13 M1 tasks are completed according to the supplied development history and inspected M1 commits through `7ad59fb`. Milestone completion does not remove sampling uncertainty or strengthen delivery guarantees. The [feasibility assessment](docs/feasibility.md) remains the earlier M0 snapshot and still lists evidence gaps; those caveats remain visible rather than being treated as resolved by this status update.

## File guide

Click a filename to inspect its implementation. All Python paths below are relative to `src/probenet/`.

### Collector, contracts and transformations

| File | What it does |
| --- | --- |
| [`collectors/subscriber.py`](src/probenet/collectors/subscriber.py) | Main runnable collector: loads measurement IDs, subscribes, queues, validates, normalizes and logs observations; reconnects on handled connection failures. |
| [`collectors/raw_capture.py`](src/probenet/collectors/raw_capture.py) | `RawCaptureWriter` saves a bounded diagnostic JSONL sample; `replay_capture()` yields original messages and receipt timestamps. |
| [`collectors/metrics.py`](src/probenet/collectors/metrics.py) | In-memory received/processed/control/invalid counters, queue occupancy, uptime and average processing rate. |
| [`contracts/atlas.py`](src/probenet/contracts/atlas.py) | Source ping, packet and result-envelope models; validates identifiers and packet counts while accepting extra source fields. The subscriber checks frame shape directly and validates payloads with `AtlasPingResult`. |
| [`contracts/normalized.py`](src/probenet/contracts/normalized.py) | Internal ping model with event/receipt times, packet counts, nullable RTT and loss ratio. |
| [`contracts/identity.py`](src/probenet/contracts/identity.py) | Provisional `(msm_id, prb_id, timestamp)` key and deterministic SHA-256 of validated payload JSON; excludes `stored_timestamp`. |
| [`transforms/ping.py`](src/probenet/transforms/ping.py) | Converts source timestamps to UTC, computes loss ratio and maps missing/negative RTT aggregates to null. Zero sent packets produce null loss. |

Identity/hash utilities are tested separately; the live collector does not yet enforce deduplication or write to a persistent sink.

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
| [`collectors/atlas_stream.py`](src/probenet/collectors/atlas_stream.py) | Connects to stream 1001 and prints decoded frames until interrupted. Earlier learning utility; use `subscriber.py` for the M1 collector. | WebSocket → terminal frames |
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
| [`.env.example`](.env.example) | Example settings; current runtime support is explained below | Reference only; not auto-loaded |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Python 3.14 setup, locked dependency sync, Ruff and pytest on main pushes/PRs | Workflow present; hosted run status not checked here |
| [`docs/event-identity.md`](docs/event-identity.md) | Key policy, payload canonicalization and historical collision analysis | M1.07 evidence |
| [`docs/delivery_guarantees.md`](docs/delivery_guarantees.md) | Failure semantics and M1 smoke-test results | Current reliability reference |
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
| [`test_packet_loss.py`](tests/unit/test_packet_loss.py) | Introductory percentage-calculation test; production loss ratios are tested in normalization tests. |

**Local verification on 2026-10-30:** Ruff passed; **26 tests passed**. Unit tests use fixtures and simulated failures; they do not prove live source completeness or durable recovery.

## Getting started and running ProbeNet

Use Python **3.14+** and `uv`, and run commands from the **local repository root** so relative configuration paths resolve. Syncing may download the locked dependencies.

```bash
uv sync --locked
uv run ruff check src tests
uv run pytest -q
```

Start the multi-measurement collector:

```bash
uv run python -m probenet.collectors.subscriber
```

It subscribes to **1001, 1004 and 1005** from [the measurement configuration](config/measurements.json), logs control messages and normalized ping summaries as JSON, and reports operational metrics every 10 seconds. Stop with **Ctrl+C**. PostgreSQL, a REST API and a dashboard are planned for M2; the current runnable product is the CLI collector. The `probenet` console command still prints a greeting.

The application queue holds at most **1,000 messages** and awaits insertion when full. Handled connection failures use exponential delays from **1 to 30 seconds**, a **15-second** connection timeout, and a delay reset after **60 seconds** connected. Normal WebSocket closure drains queued work; interruption or an unexpected failure can leave messages unprocessed. Other exceptions may terminate the process.

**Configuration boundary:** the subscriber currently hard-codes its stream URL, queue size, retry settings and log level. It does not automatically load `.env` or consume the corresponding variables listed in `.env.example`. Measurement IDs are read from JSON; the capture variables below are read from the shell environment.

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

This reads records back; it does not reinject them into normalization or recover an outage automatically. Captures can include source/destination addresses and remain under ignored `data/raw/`; operational logs belong under ignored `data/logs/`.

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

The discovery-period Nepal inventory was **111 probes**: 71 abandoned, 17 written off, 16 connected, 5 disconnected and 2 never connected; the connected cohort represented **10 IPv4 ASNs**. These are historical observations, not permanent live counts or the size of the global ingestion stream.

**Delivery guarantee: best-effort, non-durable streaming ingestion.** There is no persistent deduplication, durable event sink, exactly-once guarantee, automatic recovery of missed observations, or lossless crash handling. Metrics reset on restart. Stream warnings are counted/logged as control messages rather than independent completeness evidence. See [delivery guarantees](docs/delivery_guarantees.md) and [event identity](docs/event-identity.md).

## Architecture at a glance

| Stage | Data flow | Availability |
| --- | --- | --- |
| M1 collector | RIPE Atlas WebSocket → configured subscriber → optional bounded raw capture → bounded asyncio queue → Pydantic validation → ping normalization → structured JSON logs and in-memory metrics | Implemented |
| First MVP · M2 | Live results → validated collector → PostgreSQL → FastAPI → dashboard | Planned |
| Historical recovery · M3 | Bounded REST history → shared contracts → idempotent storage + gap reconciliation | Planned |
| Analytics and scheduling · M4–M5 | Canonical data → SQL/dbt models; Airflow coordinates bounded batch work | Planned |
| Full platform · M6 onward | Live collector → Kafka → validating consumer → ClickHouse; Parquet archives support rebuilds | Planned |

PostgreSQL becomes the control plane for catalogs, intervals and job state. Live and historical paths must share event identity and metric definitions. Additional countries use the same platform; Nepal is the first cohort. Heavy infrastructure is introduced only after the earlier product gates work locally.

## Roadmap

Milestone names and ordering follow the handbook. Expand a milestone to see the working checklist. Related handbook tasks are grouped below by outcome so this page stays readable; their original task IDs are retained.

**Status:** Completed = milestone outcomes accepted in the supplied development history; Next = upcoming work; Planned = future implementation. Completed milestones retain their documented limitations. Checklist IDs follow the handbook; M1 is expanded to show each completed task.

| Milestone | Outcome | Status |
| --- | --- | --- |
| [M0](#m0) | Verify the data and freeze a realistic scope | **Completed** |
| [M1](#m1) | Set up the repository, data contract and live collector | **Completed** |
| [M2](#m2) | Deliver the first complete working product | **Next** |
| [M3](#m3) | Make historical imports repeatable and reconcile gaps | Planned |
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

**Outcome:** a tested CLI streaming foundation. Best-effort, non-durable processing remains the explicit boundary; application persistence and persistent deduplication come later.

</details>

<a id="m2"></a>
<details open>
<summary><strong>M2 · Deliver the first complete working product — Next</strong></summary>

- [ ] **M2.01–M2.03:** Add local PostgreSQL, migrations, observation tables and metadata.
- [ ] **M2.04–M2.06:** Persist live results with idempotent writes and visible payload conflicts.
- [ ] **M2.07–M2.08:** Validate hourly RTT/loss SQL and measure indexed queries.
- [ ] **M2.09–M2.12:** Build bounded API endpoints and a dashboard with freshness/coverage, then demonstrate a clean start.

**Done when:** a real source observation reaches PostgreSQL, the API and a usable dashboard.

</details>

<a id="m3"></a>
<details>
<summary><strong>M3 · Make historical imports repeatable and reconcile gaps</strong></summary>

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
| [Delivery guarantees](docs/delivery_guarantees.md) | Current failure semantics and supplied M1 smoke-test evidence |
| [Event identity](docs/event-identity.md) | Provisional keys, hashing rules and historical validation |
| `docs/product-scope.md` · not present | Dedicated scope document referenced by the handbook; documentation gap retained |

Maintain this README as the project changes: update file purposes, statuses and milestone outcomes when evidence supports them. Detailed logs belong in `evidence/m0/`; experimental analysis belongs in the feasibility assessment. The handbook stays the roadmap reference.
