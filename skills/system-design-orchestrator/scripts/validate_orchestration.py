#!/usr/bin/env python3
"""Acceptance checks for orchestrator lifecycle state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_TOP_LEVEL = (
    "contract_version", "design_id", "mode", "status", "problem", "functional_requirements",
    "non_functional_requirements", "constraints", "out_of_scope", "assumptions", "estimates",
    "architecture", "interfaces", "data_topology", "decisions", "failure_modes",
    "validation_findings", "open_questions", "traceability",
)
COLLECTIONS = ("functional_requirements", "non_functional_requirements", "assumptions", "estimates", "decisions", "failure_modes", "validation_findings")
GATES = ("requirements", "capacity", "topology", "failure", "validator")
GATE_VALUES = {"PASS", "CONDITIONAL", "FAIL", "PENDING"}
STATUSES = {"draft", "in_progress", "validated", "complete", "blocked"}
INACTIVE = {"rejected", "deferred", "superseded", "out_of_scope", "invalidated"}
ADVANCED = re.compile(r"micro-?services?|\bshard(?:s|ed|ing)?\b|\bkafka\b|\bkinesis\b|\bpulsar\b|event[ -]stream(?:ing)?|multi[- ]region|active[- ]active|polyglot", re.I)
COMPLEXITY_FIELDS = ("rationale", "simpler_alternative", "rejection_reason", "operational_cost", "evolution_path")


def _no_duplicates(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-standard JSON constant: {name}")


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def records(state: dict, collection: str) -> list:
    value = state.get(collection)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def validate(state: object) -> list:
    if not isinstance(state, dict):
        return ["state must be an object"]
    errors: list = [f"missing top-level field {field}" for field in REQUIRED_TOP_LEVEL if field not in state]
    if state.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    if not (isinstance(state.get("design_id"), str) and re.fullmatch(r"SD-[A-Z0-9]+(?:-[A-Z0-9]+)*", state["design_id"])):
        errors.append("design_id must match SD-*")
    if state.get("mode") not in {"interview", "production"}:
        errors.append("mode must be interview or production")
    status = state.get("status")
    if status not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")
    known = {record.get("id") for collection in COLLECTIONS for record in records(state, collection)}
    for collection in COLLECTIONS:
        for record in records(state, collection):
            for reference in record.get("related_ids", []) if isinstance(record.get("related_ids"), list) else []:
                if reference not in known or reference == record.get("id"):
                    errors.append(f"{record.get('id')} has dangling or self reference {reference}")
    gates = state.get("completion_gates", {})
    if not isinstance(gates, dict):
        errors.append("completion_gates must be an object")
        gates = {}
    for gate, value in gates.items():
        if gate not in GATES:
            errors.append(f"unknown completion gate {gate}")
        elif value not in GATE_VALUES:
            errors.append(f"completion gate {gate} must be one of {sorted(GATE_VALUES)}")
    for earlier, later in zip(GATES, GATES[1:]):
        if gates.get(later) == "PASS" and gates.get(earlier) != "PASS":
            errors.append(f"gate {later} cannot PASS before gate {earlier} passes")
    questions = state.get("blocking_questions", [])
    if not isinstance(questions, list) or not all(text(item) for item in questions):
        errors.append("blocking_questions must be a list of non-empty strings")
        questions = []
    if len(questions) > 3:
        errors.append("blocking question budget exceeded")
    findings = records(state, "validation_findings")
    unresolved = [item.get("id") for item in findings if item.get("severity") in {"Critical", "High"} and item.get("status") not in {"resolved", "risk_accepted"}]
    if gates.get("validator") == "PASS" and unresolved:
        errors.append(f"validator gate PASS contradicts unresolved findings {unresolved}")
    if status in {"complete", "validated"} and gates.get("validator") != "PASS":
        errors.append(f"{status} state requires validator PASS")
    if status == "complete":
        for gate in GATES:
            if gates.get(gate) != "PASS":
                errors.append(f"complete state requires gate {gate} PASS")
        if not records(state, "failure_modes"):
            errors.append("complete state has no failure modes")
        if not findings:
            errors.append("complete state has no validator findings")
        if questions:
            errors.append("complete state still has blocking questions")
        if state.get("mode") == "production":
            for record in records(state, "failure_modes"):
                if not text(record.get("owner")):
                    errors.append(f"production completion requires an owner on {record.get('id')}")
    if status == "blocked" and not questions and not state.get("open_questions"):
        errors.append("blocked state must name the blocking or open question")
    for decision in records(state, "decisions"):
        if decision.get("status") in INACTIVE or not ADVANCED.search(str(decision.get("choice", ""))):
            continue
        identifier = decision.get("id")
        for field in COMPLEXITY_FIELDS:
            if not text(decision.get(field)):
                errors.append(f"advanced decision {identifier} lacks {field}")
        evidence = [ref for ref in decision.get("related_ids", []) if isinstance(ref, str) and ref in known and ref.split("-")[0] in {"FR", "NFR", "ASM", "EST"}]
        if not evidence:
            errors.append(f"advanced decision {identifier} lacks traceable FR/NFR/ASM/EST justification")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_orchestration.py STATE.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            state = json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(state)
    if errors:
        print("ORCHESTRATION ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("ORCHESTRATION ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
