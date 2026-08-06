# Rule Catalog v1.0

| Rule | Applies when | Severity | Required evidence |
|---|---|---|---|
| SD-R001 requirement coverage | FR/NFR exist | High | each requirement linked to decision, interface, or test |
| SD-R002 measurable NFR | NFR exists | High | metric, target, unit, window |
| SD-R003 estimate units | EST exists | Critical | dimensional formula and consistent inputs/outputs |
| SD-R004 complexity justification | advanced component/decision exists | High | threshold/risk, simpler alternative, cost, evolution path |
| SD-R005 consistency invariant | state changes or ledger/data writes exist | Critical | operation invariant and transaction boundary |
| SD-R006 resilience evidence | critical flow/dependency exists | High | FM with detection and recovery |
| SD-R007 completion gate | status is complete | Critical | validator PASS and all required phases |

A rule is skipped only when its applicability condition is false and that decision is recorded in validation notes.
