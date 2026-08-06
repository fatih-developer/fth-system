#!/usr/bin/env python3
"""Acceptance checks for capacity model JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_capacity_model.py MODEL.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        model = json.load(handle)
    errors: list[str] = []
    if model.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    scenarios = model.get("scenarios", {})
    required = {"baseline", "expected", "peak", "stress"}
    if set(scenarios) != required:
        errors.append(f"scenarios must be exactly {sorted(required)}")
    estimates = model.get("estimates", [])
    if not estimates:
        errors.append("at least one estimate is required")
    for index, estimate in enumerate(estimates):
        if not isinstance(estimate, dict):
            errors.append(f"estimate {index} must be an object")
            continue
        for field in ("id", "formula", "inputs", "unit", "horizon", "related_ids"):
            if field not in estimate:
                errors.append(f"estimate {index} missing {field}")
        if not str(estimate.get("id", "")).startswith("EST-"):
            errors.append(f"estimate {index} has invalid ID")
        if not estimate.get("related_ids"):
            errors.append(f"estimate {index} has no traceability link")
    sensitivity = model.get("sensitivity", [])
    if not isinstance(sensitivity, list) or len(sensitivity) < 3:
        errors.append("at least three sensitivity variables are required")
    if not model.get("average_peak_distinction"):
        errors.append("average_peak_distinction is required")
    if not model.get("overhead_assumptions"):
        errors.append("overhead_assumptions are required")
    if errors:
        print("CAPACITY ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("CAPACITY ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
