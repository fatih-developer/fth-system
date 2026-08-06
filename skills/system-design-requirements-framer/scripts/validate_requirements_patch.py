#!/usr/bin/env python3
"""Acceptance checks for a requirements-framer handoff envelope."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_requirements_patch.py PATCH.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        envelope = json.load(handle)
    errors: list[str] = []
    if envelope.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    patch = envelope.get("state_patch")
    if not isinstance(patch, dict):
        errors.append("state_patch must be an object")
        patch = {}
    for collection, prefix in (("functional_requirements", "FR-"), ("non_functional_requirements", "NFR-"), ("assumptions", "ASM-")):
        for index, record in enumerate(patch.get(collection, [])):
            if not isinstance(record, dict) or not str(record.get("id", "")).startswith(prefix):
                errors.append(f"{collection}[{index}] has invalid stable id")
            if isinstance(record, dict) and not all(key in record for key in ("status", "source", "confidence")):
                errors.append(f"{collection}[{index}] lacks provenance fields")
    questions = envelope.get("blocking_questions", [])
    if not isinstance(questions, list) or len(questions) > 3:
        errors.append("blocking_questions must contain at most three items")
    nfrs = patch.get("non_functional_requirements", [])
    for record in nfrs:
        if isinstance(record, dict) and not record.get("metric") and record.get("status") != "needs_measurement":
            errors.append(f"NFR {record.get('id')} is not measurable and is not marked needs_measurement")
    if errors:
        print("REQUIREMENTS ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("REQUIREMENTS ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
