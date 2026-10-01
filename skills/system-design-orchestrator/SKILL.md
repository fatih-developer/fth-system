---
name: system-design-orchestrator
description: Orchestrate a complete system-design lifecycle from requirements through workload, architecture, data consistency, failure analysis, and validation using versioned state patches and capability handoffs. Use whenever a user asks to coordinate or complete a system design, choose design-analysis capabilities, manage interview versus production mode, or determine whether a design is actually complete.
---

# System Design Orchestrator

Own the state lifecycle and phase gates. Select capabilities by need and hand off a standard envelope; do not assume sibling skills can directly call one another. Read `references/capability-map.md` for routing and `references/contract-v1.md` plus `references/handoff-v1.md` for the local contract.

## Lifecycle

1. Initialize or validate `system_design_state` and preserve its `design_id`.
2. Route requirements framing, then capacity modeling, architecture/domain decisions, data topology and consistency, failure analysis, and validation.
3. After each handoff, merge only the returned `state_patch`; preserve stable IDs and record provenance in `traceability`.
4. Limit blocking questions to three per interaction. Turn non-blocking gaps into explicit assumptions with confidence and owner.
5. Keep `interview` focused on high-impact unknowns and provisional decisions. In `production`, require evidence, operational ownership, security/compliance boundaries, recovery targets, and testable gates.
6. Do not mark `complete` until failure analysis exists, validator status is `PASS`, and all required phase gates are satisfied. A missing capability uses a safe fallback: emit the expected input/output contract, add an open question and risk, and keep status `in_progress` or `blocked`.

## Complexity rule

For microservices, sharding, Kafka/event streaming, multi-region, or polyglot persistence, require a measurable requirement, capacity threshold, risk, or organizational constraint, plus a simpler alternative, rejection reason, operational cost, and evolution path. Otherwise record the simpler architecture as the default.

## Output

Return the standard handoff envelope with `state_patch`, phase/gate status, selected capability, blocking questions, remaining risks, and validation notes. Recommend capabilities by name only; do not claim they ran unless their evidence is present in state.

## Acceptance checks

Run the bundled `scripts/validate_orchestration.py <state.json>`. Gates are `requirements`, `capacity`, `topology`, `failure`, and `validator`, valued `PASS`, `CONDITIONAL`, `FAIL`, or `PENDING`, and a gate cannot pass before the one before it. A state cannot pass orchestration acceptance when it is not a full contract state, has dangling references, asserts completion without every gate passing, failure modes, validation findings, and no blocking questions (plus FM owners in production), claims a validator PASS while Critical/High findings are unresolved, or contains an advanced complexity decision without rationale, simpler alternative, rejection reason, operational cost, evolution path, and traceable FR/NFR/ASM/EST evidence.
