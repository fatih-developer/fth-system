# fth-system

Production-oriented system design skills for requirements framing, workload modeling, architecture coordination, data topology, failure analysis, validation, and parameterized case simulation.

[![skills.sh](https://skills.sh/b/fatih-developer/fth-system)](https://skills.sh/fatih-developer/fth-system)

## Install

Install the full suite:

```bash
npx skills add fatih-developer/fth-system
```

Install one skill:

```bash
npx skills add fatih-developer/fth-system --skill system-design-orchestrator
```

## Skills

| Skill | Purpose |
|---|---|
| `system-design-requirements-framer` | Convert ambiguous problems into traceable requirements, NFRs, assumptions, and critical questions. |
| `workload-capacity-modeler` | Produce scenario-based traffic, storage, bandwidth, concurrency, cache, and sensitivity estimates. |
| `system-design-orchestrator` | Coordinate the design lifecycle through state patches, capability routing, and phase gates. |
| `distributed-data-topology-designer` | Design access-pattern-driven topology, consistency, partitioning, replication, and recovery choices. |
| `failure-mode-designer` | Model observable, recoverable failure modes and safe retry behavior. |
| `system-design-validator` | Validate traceability, units, complexity, consistency, resilience, and completion gates. |
| `system-design-case-simulator` | Generate solution-neutral, parameterized system-design cases and evaluation rubrics. |

## Contract

The suite uses versioned `system_design_state` and handoff envelope `1.0`. Specialists return `state_patch` objects; the orchestrator owns lifecycle state. Stable IDs include `FR-*`, `NFR-*`, `ASM-*`, `EST-*`, `DEC-*`, `FM-*`, and `SDV-*`.

The suite defaults to simple architectures. Microservices, sharding, Kafka/event streaming, multi-region, and polyglot persistence require measurable justification and a simpler alternative.

## Verify

```bash
python scripts/validate_curated_skills.py
python scripts/validate_system_design_contract.py tests/system-design/fixtures/low-traffic.json
python scripts/test_system_design_suite.py
```

Each skill also contains its own acceptance script and `evals/evals.json`.

For a short usage guide, see [`docs/skill-kullanim-rehberi.md`](docs/skill-kullanim-rehberi.md).

## License

MIT
