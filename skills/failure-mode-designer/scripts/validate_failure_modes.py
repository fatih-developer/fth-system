#!/usr/bin/env python3
"""Acceptance checks for failure-mode records."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_failure_modes.py FAILURE_MODEL.json")
        return 2
    with Path(sys.argv[1]).open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors: list[str] = []
    if data.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    flows = set(data.get("critical_flows", []))
    records = data.get("failure_modes", [])
    covered = {flow for record in records for flow in record.get("critical_flows", [])}
    if flows - covered:
        errors.append(f"critical flows without failure mode: {sorted(flows - covered)}")
    required = ("trigger", "blast_radius", "detection", "mitigation", "degraded_mode", "recovery", "data_impact", "test_scenario")
    for index, record in enumerate(records):
        if not str(record.get("id", "")).startswith("FM-"):
            errors.append(f"failure mode {index} has invalid ID")
        for field in required:
            if not record.get(field):
                errors.append(f"failure mode {index} missing {field}")
        retry = record.get("retry_policy")
        if record.get("retryable") and (not isinstance(retry, dict) or not all(retry.get(key) for key in ("backoff", "jitter", "budget", "idempotency"))):
            errors.append(f"failure mode {index} has unsafe retry policy")
    if errors:
        print("FAILURE ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("FAILURE ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
