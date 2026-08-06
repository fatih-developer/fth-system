# Capability Map v1

| Need | Capability | Evidence to require |
|---|---|---|
| Ambiguous scope, actors, FR/NFR | `system-design-requirements-framer` | FR/NFR/ASM patch |
| Traffic, storage, latency, growth | `workload-capacity-modeler` | EST records and scenario model |
| API protocol or interface contract | `protocol-selector`, `contract-first-designer` | DEC/contract evidence |
| Relational schema, indexes, pooling | `schema-architect`, `index-advisor`, `pgbouncer-architect` | access-pattern and capacity links |
| Delivery and dependency behavior | `webhook-architect`, `error-recovery` | retry/idempotency and recovery evidence |
| Security boundary | `security-orchestrator`, `skill-security` | security findings and ownership |
| Cross-domain design review | `plan-hardener`, `multi-brain-experts` | assumptions, trade-offs, and risks |
| Failure analysis | `failure-mode-designer` | FM records with detection and recovery |
| Consistency and topology | `distributed-data-topology-designer` | entity/operation consistency matrix |
| Rule-based completion check | `system-design-validator` | SDV findings and PASS/CONDITIONAL/FAIL |

Selection is evidence-driven. A capability is recommended when its input contract is available and the current phase has an unresolved need; no direct invocation guarantee is assumed.
