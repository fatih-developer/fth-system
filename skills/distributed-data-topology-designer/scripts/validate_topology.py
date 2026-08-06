#!/usr/bin/env python3
"""Acceptance checks for data topology decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_topology.py TOPOLOGY.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors: list[str] = []
    if data.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    if not data.get("access_patterns"):
        errors.append("access_patterns are required")
    if not data.get("hotspot_analysis"):
        errors.append("hotspot_analysis is required")
    operations = data.get("consistency_by_operation", [])
    if not operations:
        errors.append("consistency_by_operation is required")
    for index, operation in enumerate(operations):
        for field in ("operation", "invariant", "consistency", "transaction_boundary", "rpo", "rto"):
            if field not in operation:
                errors.append(f"consistency operation {index} missing {field}")
    for index, decision in enumerate(data.get("decisions", [])):
        for field in ("id", "choice", "rationale", "simpler_alternative", "tradeoff", "related_ids"):
            if field not in decision:
                errors.append(f"decision {index} missing {field}")
    if errors:
        print("TOPOLOGY ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("TOPOLOGY ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
