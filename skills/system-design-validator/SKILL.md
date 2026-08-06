---
name: system-design-validator
description: Validate a system design against versioned, applicability-aware rules for requirement coverage, units and capacity consistency, traceability, unnecessary complexity, data consistency, resilience, security boundaries, and operational feasibility. Use whenever a design needs a PASS, CONDITIONAL, or FAIL completion decision, a design review, or deterministic architecture validation.
---

# System Design Validator

Validate evidence, not intentions. Read `references/contract-v1.md`, `references/handoff-v1.md`, and `references/rule-catalog-v1.md`. Emit validator findings as `SDV-*` records in a state patch.

## Decision policy

- `FAIL` when any unresolved `Critical`, critical traceability gap, unit inconsistency, or required phase gate is missing.
- `CONDITIONAL` when unresolved `High` findings remain only with explicit risk acceptance and owner.
- `PASS` when no unresolved Critical/High findings remain and required gates are satisfied.

## Procedure

1. Determine rule applicability from the state before running a rule; do not apply every checklist item blindly.
2. Check FR/NFR coverage, measurable NFRs, EST formulas/units/scenarios, and links between requirements, assumptions, estimates, decisions, failure modes, and findings.
3. Check whether advanced complexity has a measurable rationale and simpler alternative. Flag microservices, sharding, Kafka/event streaming, multi-region, or polyglot persistence without evidence.
4. Check operation-level consistency, invariant, transaction boundary, idempotency, retry safety, detection, recovery, security boundary, and operational ownership when applicable.
5. Create one stable `SDV-*` finding per issue with rule ID, severity, evidence, affected IDs, remediation, owner, and status. Revalidation resolves findings explicitly; do not silently erase history.
6. Return the envelope with decision, gate results, remaining risks, and the next capability. Never claim PASS without evidence.

## Acceptance checks

Run bundled `scripts/validate_design.py <design.json>`. It must catch the negative fixture’s unit mismatch, reject unjustified complexity in the low-traffic fixture, and produce a PASS only for a complete state with failure and validation evidence. Also run repository and skill-creator validation.
