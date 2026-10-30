
# ProbeNet — Event Identity and Deduplication

## Logical Event Key

For the initial RIPE Atlas ping pipeline, the provisional
logical identity is:

`(msm_id, prb_id, timestamp)`

- `msm_id`: RIPE Atlas measurement identifier.
- `prb_id`: Probe identifier.
- `timestamp`: Source observation timestamp (Unix seconds).

This key identifies a candidate observation independently
of its ingestion time.

## Payload Fingerprint

ProbeNet uses SHA-256 over a canonical JSON representation
of the validated source observation.

Canonicalization:
- Sort JSON object keys.
- Use compact JSON separators.
- Exclude `stored_timestamp`.
- Preserve other validated source fields, including extras.

The payload hash helps distinguish repeated observations
from observations with the same key but changed contents.

## Duplicate Classification

- New key: First observed logical identity.
- Same key, same hash: Exact canonical-payload duplicate.
- Same key, different hash: Potential data conflict.

Conflicts must be made visible rather than silently overwritten.

## Historical Validation — M1.07

Source: Three bounded historical RIPE Atlas ping datasets
collected during M0.

Measurement IDs: 1001, 1004, 1005.

Results:

| Metric | Count |
|---|---:|
| Observations examined | 105,582 |
| Valid observations | 105,582 |
| Distinct logical keys | 105,582 |
| Repeated keys | 0 |
| Conflicting keys | 0 |
| Rejected observations | 0 |

Analysis command:

`uv run python -m probenet.discovery.check_identity`

## Limitations

1. The sample covers three public ping measurements and
   bounded historical windows, not all RIPE Atlas data.
2. The proposed key has not been proven globally unique.
3. The key may require additional discriminators for other
   measurement types or source variations.
4. Hash equality depends on the defined canonicalization
   policy. Source schema changes may affect fingerprints.
5. Excluding `stored_timestamp` is a project policy that
   deliberately ignores differences in source storage time.
6. No repeated keys appeared in this sample, so the
   historical run did not exercise real duplicate or
   conflicting-key behavior.

## Future Database Behavior

During M2, PostgreSQL will use validated logical identities
to support idempotent insertion.

Same-key/different-hash conflicts must be recorded or
reported, not silently discarded.

The identity policy will be revisited when we introduce
additional RIPE Atlas measurement types.
