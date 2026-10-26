# PROBENET

**Explore Internet latency, packet loss and data gaps using real RIPE Atlas measurements.**

PROBENET is being built as a globally capable network monitoring and analytics platform, with **Nepal as the initial implementation focus**. The goal is to make network observations useful—and show how much evidence supports each conclusion.

**Now:** source investigation and Python experiments · **First product:** M2 · **Full roadmap:** M0–M8

[Current progress](#current-progress) · [File guide](#file-guide) · [Run experiments](#run-experiments) · [Roadmap](#roadmap) · [Project references](#project-references)

## What will you be able to investigate?

- How did latency to a selected destination change during a given period?
- Did several independent probes observe packet loss, or only one?
- Which probes and networks contributed to the result?
- Is an apparent problem in the network—or is the collection pipeline missing data?

The first dashboard will focus on participating Nepal probes and curated IPv4 ping measurements. Country and ASN filters will be configurable so the platform can expand to other regions. Observations from a small probe cohort cannot establish national ISP rankings or country-wide outages.

## Current progress

| Area | What exists | Status |
| --- | --- | --- |
| Python project | Package structure, dependency declarations and uv lockfile | Scaffolded |
| Source discovery | Probe inventory, measurement discovery and configuration inspection scripts | Experimental |
| Live access | Subscriber for measurement 1001; separate throughput experiment | Experimental |
| Historical data | Three local captures with **105,582 observations** | Counts verified locally |
| Event identity | No repeated `(msm_id, prb_id, timestamp)` keys in those captures | Sample tested; replay tests pending |
| Nepal coverage | Previously reported **16 connected probes across 10 IPv4 ASNs** | Dated metadata evidence pending |
| Application | Collector contracts, persistence, API and dashboard | Planned |

**Next:** close the remaining M0 evidence gaps and freeze the MVP scope. [See the detailed feasibility assessment →](docs/feasibility.md#m0-acceptance-work-still-open)

## File guide

Click a filename to inspect its implementation. All Python paths below are relative to `src/probenet/`.

### Investigation and collector code

| File | What it does | Inputs → outputs |
| --- | --- | --- |
| [`discovery/probes.py`](src/probenet/discovery/probes.py) | Fetches all pages of probe metadata; defaults to Nepal. Reports connection status and IPv4 ASN diversity. | Probe API → terminal inventory |
| [`discovery/measurements.py`](src/probenet/discovery/measurements.py) | Finds up to 10 candidate public, running ping measurements. | Measurement API → IDs, targets, intervals and status |
| [`discovery/inspect_measurements.py`](src/probenet/discovery/inspect_measurements.py) | Inspects settings for IDs **1001, 1004 and 1005**, including target, IP family, packets and interval. | Measurement details → terminal comparison fields |
| [`discovery/historical.py`](src/probenet/discovery/historical.py) | Downloads a ten-minute window ending ten minutes before execution for all three IDs. | Results API → `data/raw/measurement_<id>.json` |
| [`discovery/throughput.py`](src/probenet/discovery/throughput.py) | Samples stream 1001 for about 60 seconds and counts result messages and UTF-8 message bytes. | Live stream → event rate, byte rate and average size |
| [`discovery/analyze_payloads.py`](src/probenet/discovery/analyze_payloads.py) | Examines saved records for fields, RTT entries, no-reply examples and repeated candidate identities. | Three local JSON captures → terminal analysis |
| [`discovery/nepal_participation.py`](src/probenet/discovery/nepal_participation.py) | Checks which currently connected Nepal probes appear in each historical capture. | Current probe metadata + local captures → probe/ASN participation |
| [`collectors/atlas_stream.py`](src/probenet/collectors/atlas_stream.py) | Connects to stream 1001 and prints decoded frames until interrupted. The robust collector is still to be built. | WebSocket → terminal frames |
| [`__init__.py`](src/probenet/__init__.py) | Defines the `probenet` console entry point; currently prints a greeting. | `probenet` command → greeting |
| [`discovery/__init__.py`](src/probenet/discovery/__init__.py) | Empty package initializer for the discovery modules. | Package structure only |

### Configuration, documentation and data

| File or folder | Purpose | Current state |
| --- | --- | --- |
| [`pyproject.toml`](pyproject.toml) | Python version requirement, dependencies, development tools and package entry point | Main project configuration |
| [`uv.lock`](uv.lock) | Records resolved dependency versions for reproducible installation | Present |
| [`.python-version`](.python-version) | Selects the project’s Python version | Python 3.14 |
| [`.gitignore`](.gitignore) | Keeps environments, Python caches, `.env` and raw captures out of Git | Configured |
| [`requirements.txt`](requirements.txt) | Reserved from the initial skeleton; dependency declarations currently live in `pyproject.toml` | Empty |
| [`README.md`](README.md) | Project entry point, file guide and development tracker | You are here |
| [`docs/feasibility.md`](docs/feasibility.md) | Detailed M0 findings, evidence quality, limitations and outstanding checks | Maintained |
| [`docs/ProbeNet_Master_Build_Handbook_v1.1.docx`](docs/ProbeNet_Master_Build_Handbook_v1.1.docx) | Original project vision, architecture and milestone definitions | Reference; unchanged |
| `data/raw/measurement_{1001,1004,1005}.json` | Existing local historical captures used by the analysis scripts | Local only; ignored by Git |
| [`evidence/m0/`](evidence/m0/) | Intended home for dated M0 logs and small evidence artifacts | `.gitkeep` only |
| [`tests/fixtures/`](tests/fixtures/) | Intended home for sanitized real records and labeled test edge cases | `.gitkeep` only |
| [`scripts/m0/`](scripts/m0/) | Reserved investigation directory from the initial skeleton; current experiments live in `src/probenet/discovery/` | `.gitkeep` only |
| `.gitkeep` files | Let Git track otherwise empty directories, including the original `docs/` skeleton | Placeholders |

<details>
<summary><strong>Other files currently in the project root</strong></summary>

`asyncio`, `json` and `time` are PostScript files generated by ImageMagick, according to their file headers. They are not Python modules or project dependencies. Their intended purpose has not been established; they have been left untouched.

</details>

## Run experiments

Use the terminal in your **local repository root**. These commands use the existing uv project; there is no application server to start yet. `uv run` may prepare the environment or install missing locked dependencies.

| Goal | Command | Needs |
| --- | --- | --- |
| Inspect saved payloads and candidate keys | `uv run python -m probenet.discovery.analyze_payloads` | Existing local captures |
| Count Nepal probes and ASNs | `uv run python -m probenet.discovery.probes` | Internet access |
| Discover public ping measurements | `uv run python -m probenet.discovery.measurements` | Internet access |
| Inspect selected configurations | `uv run python -m probenet.discovery.inspect_measurements` | Internet access |
| Measure live volume for about 60 seconds | `uv run python -m probenet.discovery.throughput` | Internet access |
| Check Nepal participation in saved history | `uv run python -m probenet.discovery.nepal_participation` | Internet access + local captures |
| Watch live frames; stop with **Ctrl+C** | `uv run python -m probenet.collectors.atlas_stream` | Internet access |

<details>
<summary><strong>Download a new historical sample</strong> — overwrites existing captures</summary>

```bash
uv run python -m probenet.discovery.historical
```

This downloads a new moving ten-minute interval for measurements 1001, 1004 and 1005. It overwrites their fixed filenames in `data/raw/`. Preserve an existing dataset before replacing it if you need repeatable analysis.

</details>

The ignored captures are absent from a clean clone. Small portable fixtures are still pending. Analysis output can contain source addresses; review it before publishing.

## Architecture at a glance

| Stage | Data flow | Availability |
| --- | --- | --- |
| Investigation | RIPE Atlas → Python scripts → terminal output / local JSON | Exists today |
| First MVP · M2 | Live results → validated collector → PostgreSQL → FastAPI → dashboard | Planned |
| Historical recovery · M3 | Bounded REST history → shared contracts → idempotent storage + gap reconciliation | Planned |
| Analytics and scheduling · M4–M5 | Canonical data → SQL/dbt models; Airflow coordinates bounded batch work | Planned |
| Full platform · M6 onward | Live collector → Kafka → validating consumer → ClickHouse; Parquet archives support rebuilds | Planned |

PostgreSQL becomes the control plane for catalogs, intervals and job state. Live and historical paths must share event identity and metric definitions. Additional countries use the same platform; Nepal is the first cohort. Heavy infrastructure is introduced only after the earlier product gates work locally.

## Roadmap

Milestone names and ordering follow the handbook. Expand a milestone to see the working checklist. Related handbook tasks are grouped below by outcome so this page stays readable; their original task IDs are retained.

**Status:** Experimental = code or a source experiment exists; In progress = evidence/scope work remains; Planned = implementation has not started. Checkboxes mark accepted outcomes, not merely files that exist.

| Milestone | Outcome | Status |
| --- | --- | --- |
| [M0](#m0) | Verify the data and freeze a realistic scope | In progress |
| [M1](#m1) | Set up the repository, data contract and live collector | Experimental scaffolding |
| [M2](#m2) | Deliver the first complete working product | Planned |
| [M3](#m3) | Make historical imports repeatable and reconcile gaps | Download experiment only |
| [M4](#m4) | Build the analytics engineering layer using SQL and dbt | Planned |
| [M5](#m5) | Orchestrate the batch pipeline with Airflow | Planned |
| [M6](#m6) | Upgrade to Kafka, ClickHouse and Parquet | Planned |
| [M7](#m7) | Make ProbeNet useful, measurable and resilient | Planned |
| [M8](#m8) | Package, document and demonstrate the complete project | Planned |

<a id="m0"></a>
<details open>
<summary><strong>M0 · Verify the data and freeze a realistic scope</strong> — current milestone</summary>

| Work | Current progress | To close |
| --- | --- | --- |
| Source documentation · M0.01 | Streaming, history and rate-limit references recorded | Finish usage/privacy review |
| Live access · M0.02 | Subscriber and reported live sample | Save acknowledgement and sanitized envelopes |
| Probe coverage · M0.03 | Nepal counts reported | Save dated metadata and neighboring-country comparison |
| Measurement selection · M0.04–M0.05 | Three candidates inspected experimentally | Save configurations and comparability decision |
| History · M0.06 | 105,582 locally verified observations | Save a request manifest and portable fixtures |
| Throughput · M0.07 | Reported 1001 baseline: 61.29 events/s | Save logs and measure selected/cohort rates |
| Payloads and identity · M0.08–M0.09 | Field inventory and historical key test | Save edge-case fixtures and test overlap/conflicts |
| Scope and verdict · M0.10–M0.12 | Global-capable, Nepal-first direction; conditional proceed | Write `docs/product-scope.md` and accept evidence |

- [ ] Source access, coverage and selected measurement configurations have saved evidence.
- [ ] Historical/live samples, result shapes and identity tests are reproducible.
- [ ] MVP story, geographic scope and exclusions are frozen.
- [ ] Feasibility verdict is reviewed and M0 is signed off.

</details>

<a id="m1"></a>
<details>
<summary><strong>M1 · Set up the repository, data contract and live collector</strong></summary>

- [ ] **M1.01–M1.03:** Finish package setup, lint/tests/CI and safe subscription configuration.
- [ ] **M1.04–M1.07:** Add fixtures, typed contracts, pure parsing, event keys and payload hashes.
- [ ] **M1.08–M1.10:** Build subscriptions with structured logs, bounded buffering, reconnects and controlled shutdown.
- [ ] **M1.11–M1.13:** Add debug capture, counters, sustained smoke-test evidence and delivery-limit documentation.

**Done when:** real input is validated and ordinary interruptions are handled in tested ways. The current print-only subscriber is a starting point.

</details>

<a id="m2"></a>
<details>
<summary><strong>M2 · Deliver the first complete working product</strong></summary>

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
| `docs/product-scope.md` · pending | Frozen MVP story, dashboard questions and exclusions |

Maintain this README as the project changes: update file purposes, statuses and milestone outcomes when evidence supports them. Detailed logs belong in `evidence/m0/`; experimental analysis belongs in the feasibility assessment. The handbook stays the roadmap reference.
