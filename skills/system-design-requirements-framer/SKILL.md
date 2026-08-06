---
name: system-design-requirements-framer
description: Turn an ambiguous system-design request into traceable functional and non-functional requirements, constraints, assumptions, scope boundaries, and a maximum of three prioritized critical questions. Use whenever a user asks to frame requirements, clarify a system architecture problem, define NFRs, or prepare a system design brief before capacity or architecture work.
---

# System Design Requirements Framer

Frame the problem before proposing architecture. Produce a `state_patch`, not a replacement state. Keep facts, assumptions, estimates, decisions, and findings distinct so later capabilities can reason over provenance.

## Contract

Use the bundled `references/contract-v1.md` and `references/handoff-v1.md`. Accept a complete or partial `system_design_state`; when absent, initialize only the minimum state and report missing inputs. Preserve `design_id`, `contract_version`, and existing stable IDs.

## Procedure

1. Extract the problem summary, scope, actors, primary flows, and explicit exclusions.
2. Create `FR-*` records for observable behavior. Split compound requirements when they have different owners, tests, or priorities.
3. Create `NFR-*` records with a metric, target, percentile/window, and scope. Mark an unmeasurable NFR as `needs_measurement`; never invent precision silently.
4. Record constraints and `ASM-*` assumptions separately. Add source, confidence, status, and related IDs.
5. Rank only the questions that can change scope, safety, capacity, consistency, or compliance. Ask at most three in one turn; convert the rest into visible assumptions or open questions.
6. In `interview` mode, optimize for the smallest useful question set and provisional prioritization. In `production` mode, add evidence, owner, operational, audit, and compliance implications where relevant.
7. Emit the standard envelope: `state_patch`, `handoff_summary`, `blocking_questions`, `remaining_risks`, `next_recommended_capability`, and `validation_notes`.

## Acceptance checks

Run the bundled `scripts/validate_requirements_patch.py <patch.json>` and the repository's curated-skill validator. A patch is accepted only when every requirement has a stable ID, measurable NFR gaps are explicit, assumptions are not presented as facts, question count is at most three, and the contract version is `1.0`.

## Handoff

Recommend `workload-capacity-modeler` when requirements contain workload-relevant signals, otherwise recommend the missing capability that resolves the highest-risk open question. Do not claim the design is complete.
