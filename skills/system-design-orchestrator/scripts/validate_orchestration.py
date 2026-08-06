#!/usr/bin/env python3
"""Acceptance checks for orchestrator lifecycle state."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_orchestration.py STATE.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        state = json.load(handle)
    errors: list[str] = []
    gates = state.get("completion_gates", {})
    if state.get("status") == "complete":
        if not state.get("failure_modes"):
            errors.append("complete state has no failure modes")
        if not state.get("validation_findings"):
            errors.append("complete state has no validator findings")
        if gates.get("validator") != "PASS":
            errors.append("complete state requires validator PASS")
    for decision in state.get("decisions", []):
        choice = str(decision.get("choice", "")).lower()
        advanced = any(term in choice for term in ("microservice", "shard", "kafka", "multi-region", "polyglot"))
        if advanced and not decision.get("rationale"):
            errors.append(f"advanced decision {decision.get('id')} lacks rationale")
        if advanced and not decision.get("simpler_alternative"):
            errors.append(f"advanced decision {decision.get('id')} lacks simpler alternative")
    if len(state.get("blocking_questions", [])) > 3:
        errors.append("blocking question budget exceeded")
    if errors:
        print("ORCHESTRATION ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("ORCHESTRATION ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
