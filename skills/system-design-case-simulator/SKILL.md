---
name: system-design-case-simulator
description: Generate and run parametrically varied system-design case briefs across domains and scale profiles, with interview or production mode, injected constraints, change events, rubric, and core-contract-compatible state. Use whenever someone needs system-design training cases, scenario simulation, growth shocks, dependency outages, requirement changes, or repeatable architecture evaluation.
---

# System Design Case Simulator

Generate one parameterized case engine, not one skill per case study. Read `references/contract-v1.md` and `references/handoff-v1.md`. Keep the brief solution-neutral so the learner must derive the architecture.

## Inputs and behavior

Accept domain, users, request rate, read/write ratio, payload, growth, retention, consistency, availability, latency, geography, compliance, team maturity, budget, mode, and variation. Normalize the parameters into a stable `design_id` and contract v1 state or a brief that can initialize one.

Support at least `baseline`, `growth_shock`, `dependency_outage`, and `requirement_change` variations. Make parameter changes visible in expected decision areas, not in a hidden answer. In `interview`, inject no more than three critical questions; in `production`, add evidence and operational acceptance expectations.

## Procedure

1. Validate domain and scale inputs; use bounded defaults only when disclosed as assumptions.
2. Generate problem brief, actors, constraints, change event, decision areas, and evaluation rubric. Do not prescribe a vendor or architecture as the answer.
3. Include expected dimensions such as workload, topology, consistency, failure handling, security/compliance, and operations based on applicability.
4. Emit the handoff envelope and a deterministic case artifact. Preserve the state identity across variations when a base design is supplied.

## Acceptance checks

Run bundled `scripts/generate_case.py --input <params.json> --output <case.json>` and `scripts/validate_case.py <case.json>`. Acceptance requires four domains, parameter-sensitive decision areas, four variations, both modes, and contract-compatible identity.
