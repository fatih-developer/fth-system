#!/usr/bin/env python3
"""Acceptance checks for generated cases."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from generate_case import MAX_INTERVIEW_QUESTIONS, VARIATIONS, case_id, validate_params

REQUIRED_TOP_LEVEL = (
    "contract_version", "design_id", "mode", "status", "problem", "functional_requirements",
    "non_functional_requirements", "constraints", "out_of_scope", "assumptions", "estimates",
    "architecture", "interfaces", "data_topology", "decisions", "failure_modes",
    "validation_findings", "open_questions", "traceability",
)
DESIGN_COLLECTIONS = ("estimates", "decisions", "failure_modes", "validation_findings")
VENDORS = re.compile(r"\b(?:kafka|redis|memcached|cassandra|dynamodb|postgres(?:ql)?|mysql|mongodb|kubernetes|elasticsearch|rabbitmq|kinesis|spanner|cockroachdb|s3)\b", re.I)


def validate(case: object) -> list:
    if not isinstance(case, dict):
        return ["case must be an object"]
    errors = [f"missing top-level field {field}" for field in REQUIRED_TOP_LEVEL if field not in case]
    params = case.get("parameters")
    errors += [f"parameters: {error}" for error in validate_params(params)]
    if case.get("contract_version") != "1.0" or not re.fullmatch(r"SD-SIM-[0-9A-F]{10}", str(case.get("design_id", ""))):
        errors.append("case identity is not contract-compatible")
    elif isinstance(params, dict) and case["design_id"] != case_id(params):
        errors.append("design_id does not match the parameters it was generated from")
    if isinstance(params, dict):
        if case.get("mode") != params.get("mode"):
            errors.append("mode does not match parameters")
        variation = case.get("variation")
        if not isinstance(variation, dict) or variation.get("name") != params.get("variation") or variation.get("injected_change") != VARIATIONS.get(params.get("variation")):
            errors.append("variation does not match parameters")
    if case.get("status") != "draft":
        errors.append("a generated case must start as draft")
    for collection in DESIGN_COLLECTIONS:
        if case.get(collection):
            errors.append(f"{collection} must be empty so the brief stays solution-neutral")
    if set(case.get("variation_catalog", [])) != set(VARIATIONS):
        errors.append("variation catalog incomplete")
    if set(case.get("supported_modes", [])) != {"interview", "production"}:
        errors.append("mode support incomplete")
    areas = case.get("decision_areas", [])
    if not isinstance(areas, list) or len(areas) < 5 or len(set(areas)) != len(areas):
        errors.append("decision areas must be at least five distinct entries")
    rubric = case.get("rubric", {})
    if not isinstance(rubric, dict) or not rubric or not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in rubric.values()) or sum(rubric.values()) != 100:
        errors.append("rubric must be positive integer weights totalling 100")
    questions = case.get("open_questions", [])
    if case.get("mode") == "interview" and len(questions) > MAX_INTERVIEW_QUESTIONS:
        errors.append(f"interview cases may inject at most {MAX_INTERVIEW_QUESTIONS} critical questions")
    brief = json.dumps({key: case.get(key) for key in ("problem", "decision_areas", "variation", "open_questions")})
    vendor = VENDORS.search(brief)
    if vendor:
        errors.append(f"brief prescribes a vendor ({vendor.group(0)}); keep it solution-neutral")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_case.py CASE.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            case = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(case)
    if errors:
        print("SIMULATOR ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("SIMULATOR ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
