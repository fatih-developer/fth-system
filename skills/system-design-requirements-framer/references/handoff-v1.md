# Handoff Envelope v1.0

Return an object containing:

```json
{
  "contract_version": "1.0",
  "state_patch": {},
  "handoff_summary": "short summary",
  "blocking_questions": [],
  "remaining_risks": [],
  "next_recommended_capability": "workload-capacity-modeler",
  "validation_notes": []
}
```

`state_patch` may add or update records but must preserve stable IDs and must not silently delete records owned by another capability. A direct call with no state must say which minimum fields were initialized or remain missing.
