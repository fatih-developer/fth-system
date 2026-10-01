---
name: workload-capacity-modeler
description: Model system workload and capacity with baseline, expected, peak, and stress scenarios, explicit formulas and units, storage/replication overhead, cache and concurrency assumptions, and sensitivity analysis. Use whenever a system design needs traffic estimates, sizing, throughput, bandwidth, retention, cache, concurrency, growth, or capacity justification.
---

# Workload Capacity Modeler

Turn workload assumptions into inspectable ranges and estimates. Produce a `state_patch`; never replace the full design state or present a single guessed number as fact.

## Contract

Read the bundled `references/contract-v1.md` and `references/handoff-v1.md`. Preserve `design_id`, stable requirement/assumption IDs, and contract version `1.0`. Attach every `EST-*` record to at least one `FR-*`, `NFR-*`, or `ASM-*`.

## Procedure

1. Extract request rate, read/write ratio, payload size, active users, concurrency, growth, retention, availability, and geography. Mark missing inputs as assumptions with ranges.
2. Create `baseline`, `expected`, `peak`, and `stress` scenarios. Keep average and peak rates separate and state the time window for each.
3. For every estimate, show formula, named inputs with units, declared value and unit, scenario, horizon, source, confidence, and sensitivity impact, following `references/estimate-units-v1.md`. Keep bytes, bits, seconds, requests, and events dimensionally consistent; never hide a unit conversion in a numeric literal.
4. Model storage as logical payload plus index, metadata, replication, and operational overhead. Model bandwidth in bits/s or bytes/s consistently and identify egress versus ingress.
5. Model concurrency from arrival rate and latency assumptions; state whether the result is a Little's Law estimate, a limit, or an observed measurement.
6. Evaluate cache capacity and hit-rate effects only when the access pattern supports caching. Do not infer cache correctness from cache presence.
7. Rank at least the three variables with the largest outcome impact. Use intervals where input uncertainty is material.
8. Recommend the next capability without directly calling it. Emit the standard handoff envelope.

## Complexity discipline

Capacity alone does not authorize microservices, Kafka, sharding, or multi-region. Record a `DEC-*` only when a measurable threshold, risk, or organizational constraint supports it, and record a simpler alternative.

## Acceptance checks

Run the bundled `scripts/validate_capacity_model.py <model.json>`, the repository's curated-skill validator, and the contract validator. Accept only when all four scenarios exist with a window and the same unit-bearing inputs that never decrease from baseline to stress; every scenario has an estimate; every estimate passes the dimensional check, agrees with its scenario inputs, and links to an FR, NFR, or ASM; average versus peak is explicit; index, metadata, and replication overhead are visible; and at least three distinct sensitivity variables are ranked 1..N.
