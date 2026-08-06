---
name: distributed-data-topology-designer
description: Design data topology from access patterns and capacity evidence, including storage choice, partitioning, replication, indexes, lifecycle, entity-level consistency, transaction boundaries, conflict strategy, RPO, and RTO. Use whenever a system design needs database topology, sharding, replication, consistency, partition-key, or data placement decisions.
---

# Distributed Data Topology Designer

Design data placement from workload and invariants, not from fashionable technologies. Read `references/contract-v1.md` and `references/handoff-v1.md`; return a `state_patch` that preserves existing IDs.

## Procedure

1. Inventory entities, read/write access patterns, cardinality, payload, lifecycle, locality, and ownership.
2. Map each important operation to storage needs, indexes, partition key, expected volume, and hotspot risk.
3. For each critical entity or operation, state invariant, consistency level, transaction boundary, conflict strategy, acceptable replication lag, RPO, and RTO.
4. Treat replication and sharding as independent decisions. Choose the simplest topology that meets the traced workload and recovery requirements.
5. For every advanced distribution decision, record `DEC-*`, measurable rationale, simpler alternative, rejected reason, operational cost, and evolution path.
6. Identify data residency, audit, deletion, backup, and lifecycle implications. Flag missing evidence as assumptions or open questions.
7. Emit the standard handoff envelope and recommend failure analysis when topology risks remain.

## Acceptance checks

Run bundled `scripts/validate_topology.py <topology.json>`, contract validation, the repository validator, and skill-creator quick validation. Accept only when access patterns, hotspot analysis, operation-level consistency, and trade-offs are present.
