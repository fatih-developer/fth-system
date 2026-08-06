#!/usr/bin/env python3
"""Acceptance checks for generated cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_case.py CASE.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        case = json.load(handle)
    errors: list[str] = []
    if case.get("contract_version") != "1.0" or not str(case.get("design_id", "")).startswith("SD-SIM-"):
        errors.append("case identity is not contract-compatible")
    if set(case.get("variation_catalog", [])) != {"baseline", "growth_shock", "dependency_outage", "requirement_change"}:
        errors.append("variation catalog incomplete")
    if set(case.get("supported_modes", [])) != {"interview", "production"}:
        errors.append("mode support incomplete")
    if len(case.get("decision_areas", [])) < 5:
        errors.append("decision areas are not comprehensive")
    if sum(case.get("rubric", {}).values()) != 100:
        errors.append("rubric must total 100")
    if errors:
        print("SIMULATOR ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("SIMULATOR ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
