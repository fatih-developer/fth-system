#!/usr/bin/env python3
"""Small deterministic rule runner for validator acceptance fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def finding(rule: str, severity: str, evidence: str, related: list[str]) -> dict[str, object]:
    return {"rule": rule, "severity": severity, "evidence": evidence, "related_ids": related}


def run(state: dict[str, object]) -> tuple[str, list[dict[str, object]]]:
    findings: list[dict[str, object]] = []
    nfrs = state.get("non_functional_requirements", [])
    for nfr in nfrs if isinstance(nfrs, list) else []:
        if isinstance(nfr, dict) and not nfr.get("metric") and nfr.get("status") != "needs_measurement":
            findings.append(finding("SD-R002", "High", f"{nfr.get('id')} has no metric", [str(nfr.get("id"))]))
    estimates = state.get("estimates", [])
    for estimate in estimates if isinstance(estimates, list) else []:
        if isinstance(estimate, dict):
            formula = str(estimate.get("formula", ""))
            if " / 60" in formula and estimate.get("unit") == "events/s" and "per minute" in str(estimate.get("inputs", "")):
                findings.append(finding("SD-R003", "Critical", f"{estimate.get('id')} mixes per-minute input with per-second result", [str(estimate.get("id"))]))
    for decision in state.get("decisions", []) if isinstance(state.get("decisions"), list) else []:
        if isinstance(decision, dict):
            choice = str(decision.get("choice", "")).lower()
            if any(term in choice for term in ("microservice", "shard", "kafka", "multi-region", "polyglot")) and not all(decision.get(key) for key in ("rationale", "simpler_alternative", "tradeoff", "evolution_path")):
                findings.append(finding("SD-R004", "High", f"{decision.get('id')} lacks complexity evidence", [str(decision.get("id"))]))
    if state.get("status") == "complete":
        gates = state.get("completion_gates", {})
        if not state.get("failure_modes") or not state.get("validation_findings") or not isinstance(gates, dict) or gates.get("validator") != "PASS":
            findings.append(finding("SD-R007", "Critical", "complete status lacks failure, validator, or gate evidence", []))
    if any(item["severity"] == "Critical" for item in findings):
        return "FAIL", findings
    if any(item["severity"] == "High" for item in findings):
        return "CONDITIONAL", findings
    return "PASS", findings


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_design.py DESIGN.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        state = json.load(handle)
    decision, findings = run(state)
    print(json.dumps({"decision": decision, "findings": findings}, indent=2))
    if state.get("expected_decision") and state["expected_decision"] != decision:
        print(f"EXPECTED {state['expected_decision']} BUT GOT {decision}")
        return 1
    print(f"VALIDATOR ACCEPTANCE PASSED: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
