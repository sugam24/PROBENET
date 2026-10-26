# PROBENET M0 feasibility assessment

Reviewed locally on 2026-10-26 against the complete [Master Build Handbook v1.1](ProbeNet_Master_Build_Handbook_v1.1.docx), the repository scripts and three existing historical captures. The README preserves the handbook’s detailed milestone IDs.

## Verdict and evidence status

**Proceed with a globally capable platform, initially focused on participating Nepal probes. Source access and useful historical ping data are supported; formal M0 acceptance remains open.** This is a feasibility decision, not a claim that the collector, MVP or recovery platform is implemented.

Evidence labels used below:

- **Verified locally:** recounted directly from existing capture files or confirmed by source inspection during this review.
- **Reported observation:** retained from the pre-existing feasibility report; original logs or metadata snapshots were not available to independently reproduce it.
- **Decision:** current project scope or engineering choice.
- **Pending:** evidence or implementation still required.

No additional experiment results accompanied the latest documentation request. Existing results have been preserved with their provenance rather than presented as new live measurements. No fresh probe or measurement discovery run was performed during this review.

## Source documentation and constraints — M0.01

Reviewed official streaming, historical results and rate-limit pages on 2026-10-26:

- [Streaming API](https://atlas.ripe.net/docs/apis/streaming-api/): HTTP GET and WebSocket access; messages use a type/payload array; a subscription acknowledgement is distinct from a result. Include a client identifier. A subscription or short sample does not prove complete delivery.
- [Results and latest](https://atlas.ripe.net/docs/apis/rest-api-manual/measurements/results-and-latest/): historical results support `start`, `stop` and `probe_ids`. Generic pagination/field-selection parameters do not apply; large responses are streamed by the server. The existing Python script nevertheless buffers the entire decoded response, so keep windows small.
- [REST rate limiting](https://atlas.ripe.net/docs/apis/rest-api-manual/core-concepts/rate-limiting/): HTTP 429 requires backing off. Cache metadata, avoid tight polling and use the stream for live results. No fixed numeric read quota was established by this review.

Additional authoritative references remain to be fully reviewed and recorded before M0.01 sign-off:

- [Measurement overview](https://atlas.ripe.net/docs/apis/rest-api-manual/measurements/)
- [Probe listing](https://atlas.ripe.net/docs/apis/rest-api-manual/probes/listing-probes/)
- [Anonymous access and privacy](https://atlas.ripe.net/docs/apis/rest-api-manual/authentication/anonymous-access/)
- [Result format](https://atlas.ripe.net/docs/apis/measurement-result-format/version-5000/)
- [Service terms](https://www.ripe.net/about-us/legal/ripe-atlas-service-terms-and-conditions/)

The service-terms page fetch timed out during this review. The handbook states that commercial use requires prior permission and public probe coordinates are offset for privacy; retain those as handbook guidance pending direct verification of current terms. Do not infer unrestricted use from public access. Source IP addresses should not be exposed unnecessarily in published fixtures or dashboard responses.

## Stream and measurement selection — M0.02, M0.04, M0.05

Reported candidate settings: public ICMP ping, IPv4, 240-second interval, three configured packets, with measurements 1001, 1004 and 1005 targeting K, F and I DNS root servers respectively. Save the exact measurement API responses to confirm target mapping, current running/public state, protocol, packet size and configuration details before freezing subscriptions. Historical captures establish sampled ping results, not current measurement status.

Relevant implementations:

- `src/probenet/collectors/atlas_stream.py`: sends a subscription for 1001 and prints every decoded frame. Its “Subscribed” print follows sending the request; it does not validate the server acknowledgement. No reconnect, structured logging, bounded processing queue or durable sink exists.
- `src/probenet/discovery/measurements.py`: discovers candidate public running pings.
- `src/probenet/discovery/inspect_measurements.py`: prints selected configuration fields for the three IDs.

Reported live access is supported by the prior throughput observation, but no saved stream acknowledgement or redacted live envelope was found. Preserve those artifacts under `evidence/m0/` before closing M0.02.

Compare the same measurement over time and explicitly selected cohorts. The three destinations differ; differences between their RTTs do not isolate ISP performance. A shared interval and packet setting alone are insufficient to justify cross-target comparisons.

## Nepal coverage — M0.03, M0.10

Reported inventory:

- 111 registered Nepal probes.
- 16 connected probes across 10 distinct IPv4 ASNs.
- All 16 appeared in each of the three sampled measurement histories.

`probes.py` paginates probe metadata and `nepal_participation.py` intersects connected Nepal probe IDs with historical participant IDs. The latter fetches current metadata, so rerunning later can change the cohort without any change to the historical files. A dated inventory snapshot, original probe list and participation output were not found. The historical files alone cannot verify Nepal location or ASN diversity.

No neighboring-country results were found. Save dated inventories and errors for a clearly named comparison cohort before closing M0.03. Sixteen probes are a useful initial investigation cohort, not evidence of representative national or ISP coverage. There is no established minimum sample threshold for regional claims yet.

**Scope decision:** preserve global-capable ingestion/contracts and configurable geography; initially store and analyze the Nepal cohort. Assess coverage on every analysis window and revisit regional expansion when evidence supports it. The existing historical captures are global measurement samples, not Nepal-filtered data. Ingest filtering and retention are still unimplemented.

## Historical samples — M0.06

Verified locally from ignored files under `data/raw/`:

- Measurement 1001: 35,130 observations from 14,086 unique probes.
- Measurement 1004: 35,236 observations from 14,085 unique probes.
- Measurement 1005: 35,216 observations from 14,083 unique probes.

Total: **105,582 observations**. All sampled records have `type=ping` and `af=4`. Each file’s minimum/maximum source timestamps are 1793028291 and 1793028891, spanning 600 seconds. These are observed event bounds, not a saved request manifest or proof that every source observation is present.

`historical.py` requests a ten-minute window ending ten minutes before execution and saves each measurement separately. It does not persist the request timestamps, headers, execution environment or completion manifest. It overwrites the same file names on subsequent runs. The original report described a ten-minute retrieval; the event bounds are consistent with that description, but exact request provenance cannot be reconstructed from them alone.

Local SHA-256 fingerprints, to identify the reviewed dataset:

```text
measurement_1001.json  f801c32b210f79eb6e16dcb4782fc614ae4c746ac52630f65989241eb96aaa85
measurement_1004.json  4678a629761449163a133f2121f8fe1bdc6e642739d45dbce61d0f665ccf805f
measurement_1005.json  4afa4bef739dab016aad51dfab3895b8549b06fbbaafc597216c49e54644c845
```

The files remain ignored by `/data/raw/`. A clean clone cannot reproduce these checks without captures. `tests/fixtures/` contains only `.gitkeep`; small sanitized portable fixtures and a capture manifest remain required.

## Live throughput — M0.07

Reported for measurement 1001 over approximately 60 seconds:

- 3,688 result events; 61.29 events/s.
- 25.87 KiB/s; average event size approximately 432 bytes.

The original throughput log, exact start/end time and byte total were not found. `throughput.py` counts UTF-8 bytes of complete `atlas_result` messages, including their JSON envelopes; it excludes control frames, transport overhead and compression effects. Its output labels the binary rate `KB/sec`; this assessment uses the accurate unit KiB/s.

At the reported byte rate, continuous capture would be approximately 2.29 decimal GB/day for this one unfiltered stream, before storage overhead and extra copies. This is an extrapolation, not measured daily storage consumption. The baseline cannot be multiplied into a guaranteed combined rate for three subscriptions and does not establish Nepal-filtered rates, bursts, peak capacity or sustained reliability. Save a longer bounded run and measure the selected cohort before fixing retention or capacity targets.

## Payload inventory and edge cases — M0.08

Verified fields present in all sampled observations: `fw`, `lts`, `dst_name`, `af`, `dst_addr`, `src_addr`, `proto`, `size`, `result`, `dup`, `rcvd`, `sent`, `min`, `max`, `avg`, `msm_id`, `prb_id`, `timestamp`, `msm_name`, `from`, `type`, `step`, `stored_timestamp`. `mver` and `ttl` are optional in these captures. Field presence does not establish validity or identical semantics across other measurement types.

Using the investigation script’s criterion of at least one packet dictionary containing an `rtt` key:

- 1001: 34,239 observations with an RTT entry; 891 without. Negative `avg`: 894.
- 1004: 34,519 with an RTT entry; 717 without. Negative `avg`: 721.
- 1005: 34,077 with an RTT entry; 1,139 without. Negative `avg`: 1,145.

An `rtt` key’s presence alone is not validation of a successful numeric RTT. No-reply classification and negative aggregate sentinel counts differ; preserve them as separate findings. No top-level `error` keys appeared in the sampled records. Packet-level errors/timeouts and malformed/control frames still need explicit fixture coverage; absence of a top-level error does not mean error-free measurements.

Observed `sent` counts vary despite the reported three-packet configuration:

- 1001: 34,988 records with 3; 116 with 2; 12 with 1; 14 with 0.
- 1004: 35,056 with 3; 148 with 2; 20 with 1; 12 with 0.
- 1005: 35,061 with 3; 125 with 2; 20 with 1; 10 with 0.

Contract implications, still to be implemented in M1:

- Preserve raw fields and provenance; distinguish event, receipt and persistence time.
- Convert absent/negative aggregate RTT to nullable normalized values with status; never zero latency.
- Define loss from validated packet counts, using null/invalid treatment when `sent=0`.
- Keep observed no-reply results distinct from missing stream data, probe disconnection and pipeline gaps.
- Preserve unknown optional fields and classify invalid required fields.

## Candidate identity — M0.09

Candidate ping identity: `(msm_id, prb_id, timestamp)`.

Verified locally: zero repeated candidate identities within each file and across the combined 105,582 observations. All three identity components are present in this sample. This establishes sample uniqueness only; it does not prove the identity across every result type, firmware variant, historical correction or same-second event.

Next tests: live/history overlap, reconnection, replayed duplicates, same-key/different-payload conflicts and any required subtype discriminator. Keep a separate canonicalized payload hash so variants cannot be hidden by deduplication. Idempotent persistence and conflict handling do not exist yet. A duplicate-free download is not a replay-safety demonstration.

## MVP story and exclusions — M0.11

Proposed user story: a learner selects one curated ping measurement and a UTC window, examines participating Nepal probes and ASNs, and investigates a change in RTT or packet loss while checking sample counts, source freshness and pipeline uncertainty.

Dashboard questions:

1. How did a fixed destination’s observed latency change over time?
2. Which participating probes saw missing replies or packet loss?
3. How many probes, ASNs and observations support the displayed window?
4. Could missing pipeline data explain an apparent change?

A valid investigation compares a measurement with itself across time using an explicit cohort, then checks independent probe observations and pipeline gaps before suggesting an anomaly. An anomaly is evidence to investigate, not a diagnosis.

Initial exclusions: DNS/traceroute product features, all-Atlas ingestion, paid measurement scheduling, national outage guarantees, ISP rankings from unlike targets, ML predictions, Kubernetes and cloud deployment. Kafka, ClickHouse, Parquet, dbt and Airflow remain in the full roadmap at their original milestones, outside the first MVP infrastructure.

`docs/product-scope.md` still needs an explicit acceptance story, metric definitions, filters, empty/stale states and exclusions before M0.11 closes. This assessment records the current direction but does not substitute for that deliverable.

## M0 acceptance work still open

- M0.01: finish and record direct usage/privacy/format review; resolve terms fetch failure.
- M0.02: save actual subscription acknowledgement and sanitized live result envelopes.
- M0.03: save Nepal metadata/participation evidence and neighboring-country comparison.
- M0.04–M0.05: save metadata/configuration snapshots and a full comparability decision.
- M0.06: preserve a bounded capture manifest and small sanitized fixtures without overwriting the audited dataset.
- M0.07: save throughput logs, timestamps and combined/cohort rates; define bounded retention assumptions.
- M0.08: extract real success, timeout and error fixtures; label synthetic malformed test inputs separately.
- M0.09: record overlap/replay/conflict tests and identity limitations.
- M0.10–M0.11: finalize configurable Nepal-first scope and write the product-scope document.
- M0.12: review the evidence and record formal checkpoint sign-off separately from this conditional proceed decision.

## Reproducing the existing local analysis

From the repository root, with dependencies already available:

```bash
uv run python -m probenet.discovery.analyze_payloads
```

This reads the three local files and prints per-measurement field counts, candidate identity counts and payload examples. Its examples may include source addresses; sanitize output before publishing. It is an investigation utility, not an automated acceptance test. Save the dataset hashes and environment with future outputs. Do not rerun the historical downloader merely to reproduce this fixed dataset: it selects a new moving interval.

## Handbook alignment and current implementation boundary

The handbook remains unchanged. Its intended progression is M0 feasibility → M1 collector/contracts → M2 PostgreSQL/API/dashboard MVP → M3 historical recovery → M4 SQL/dbt → M5 Airflow → M6 Kafka/ClickHouse/Parquet → M7 product reliability → M8 release.

The previous report’s Nepal focus is an implementation cohort within a global-capable project. Existing scripts under `src/probenet/discovery/` and local `data/raw/` files are experiments; they do not complete production milestones. Evidence continues to use the existing `evidence/m0/` directory rather than the handbook’s example `docs/evidence/M0/`. This file is the maintained feasibility assessment despite later handbook chapters also referring to `docs/source-feasibility.md`.
