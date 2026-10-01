# Rule Catalog v1.0

`scripts/validate_design.py` implements every rule below. A rule is skipped only when its applicability condition is false, and the skip is recorded in `rules` and `validation_notes` of the output.

| Rule | Applies when | Severity | Required evidence |
|---|---|---|---|
| SD-R000 contract conformance | always | Critical | all contract v1.0 top-level fields, `SD-*` design ID, mode/status enums, family-prefixed unique stable IDs, `status`/`source`/`confidence` on every record. Other rules run only when this passes. |
| SD-R001 requirement coverage | an in-force FR or NFR exists | High | each requirement is in `related_ids` of a decision, interface, or failure mode, or is an endpoint of a `traceability` edge. Estimates size requirements but do not cover them. |
| SD-R002 measurable NFR | an in-force NFR exists | High | `metric`, numeric `target`, `unit`, and `window`; or status `needs_measurement` with a `measurement_gap`. |
| SD-R003 estimate units | an in-force EST exists | Critical | formula, inputs, value, and unit that pass the dimensional check in `references/estimate-units-v1.md`, plus `horizon` and `related_ids`. |
| SD-R004 complexity justification | an in-force decision chooses, or `architecture`/`data_topology` describes, microservices, sharding, event streaming (Kafka, Kinesis, Pulsar), multi-region/active-active, or polyglot persistence | High | `rationale`, `simpler_alternative`, `rejection_reason`, `operational_cost`, `evolution_path`, and at least one existing FR/NFR/ASM/EST in `related_ids`. |
| SD-R005 consistency invariant | an in-force FR changes state (create, update, delete, write, transfer, pay, ingest, ...) or `data_topology.consistency_by_operation` exists | Critical | every state-changing FR is linked from an operation with `invariant`, `consistency`, and `transaction_boundary`. Value-moving FRs (ledger, transfer, payment, balance) also need strong consistency and an `idempotency` key. |
| SD-R006 resilience evidence | an in-force FR exists (unless marked `"critical": false`, which is noted) or `architecture.dependencies` is non-empty | High | each critical FR is in `related_ids` of an FM with `detection` and `recovery`; each dependency is named by an FM `dependency`. |
| SD-R007 completion gate | status is `validated` or `complete` | Critical | `completion_gates.validator` is PASS. For `complete`, the requirements, capacity, topology, and failure gates are also PASS; FM and SDV records exist; no unresolved Critical/High SDV, no risk-accepted Critical, no `needs_measurement` NFR, and no open blocking question. |
| SD-R008 decision conflict | an in-force decision exists | Critical / High | in-force decisions with the same `topic` and different `choice` are Critical; same choice twice is a High duplicate; a decision without `topic` and `choice` is High. |
| SD-R009 traceability integrity | always (after SD-R000) | Critical | every `related_ids` entry, estimate input `source`, and `traceability` endpoint names an existing stable ID; no self-references. |

In-force means the record status is not `rejected`, `deferred`, `superseded`, `out_of_scope`, or `invalidated`.

## Decision policy

- `FAIL`: any Critical finding, or any High finding without a matching risk acceptance.
- `CONDITIONAL`: only High findings remain, and each one is covered by a risk acceptance.
- `PASS`: no findings.

A risk acceptance is an `SDV-*` record in the state with status `risk_accepted`, the same `rule`, `related_ids` covering the finding, a non-empty `owner`, and a non-empty `risk_acceptance` statement. A Critical finding can never be risk-accepted.

## Finding format

Each finding has a stable ID `SDV-<rule number>-<related IDs>` (for example `SDV-R003-EST-001`, or `SDV-R007-STATE` when no record is involved), `rule`, `severity`, `evidence`, `related_ids`, `remediation`, `owner`, and `status` (`open` or `risk_accepted`). Re-running validation on an unchanged state reproduces the same IDs.
