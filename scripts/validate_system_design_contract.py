#!/usr/bin/env python3
"""Deterministic checks for the v1 system-design state and handoff contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "tests" / "system-design" / "contract-schema.json"

REQUIRED_TOP_LEVEL = {
    "contract_version", "design_id", "mode", "status", "problem", "functional_requirements",
    "non_functional_requirements", "constraints", "out_of_scope", "assumptions", "estimates",
    "architecture", "interfaces", "data_topology", "decisions", "failure_modes",
    "validation_findings", "open_questions", "traceability",
}
ID_PREFIXES = {
    "functional_requirements": "FR-",
    "non_functional_requirements": "NFR-",
    "assumptions": "ASM-",
    "estimates": "EST-",
    "decisions": "DEC-",
    "failure_modes": "FM-",
    "validation_findings": "SDV-",
}


def load(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_state(state: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be an object"]
    missing = REQUIRED_TOP_LEVEL - set(state)
    errors.extend(f"missing top-level field: {field}" for field in sorted(missing))
    if state.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    if state.get("mode") not in {"interview", "production"}:
        errors.append("mode must be interview or production")
    if not isinstance(state.get("design_id"), str) or not state.get("design_id"):
        errors.append("design_id must be a non-empty string")
    seen: set[str] = set()
    for field, prefix in ID_PREFIXES.items():
        records = state.get(field, [])
        if not isinstance(records, list):
            errors.append(f"{field} must be an array")
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(f"{field}[{index}] must be an object")
                continue
            identifier = record.get("id")
            if not isinstance(identifier, str) or not identifier.startswith(prefix):
                errors.append(f"{field}[{index}].id must start with {prefix}")
            elif identifier in seen:
                errors.append(f"duplicate stable id: {identifier}")
            else:
                seen.add(identifier)
            for required in ("status", "source", "confidence"):
                if required not in record:
                    errors.append(f"{field}[{index}] missing {required}")
    return errors


def validate_patch(patch: object) -> list[str]:
    if not isinstance(patch, dict):
        return ["state_patch must be an object"]
    if "contract_version" in patch and patch["contract_version"] != "1.0":
        return ["state_patch contract_version must be 1.0"]
    return []


def main() -> int:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        paths = [ROOT / "tests" / "system-design" / "fixtures" / "low-traffic.json"]
    errors: list[str] = []
    if not SCHEMA.exists():
        errors.append(f"schema missing: {SCHEMA}")
    else:
        schema = load(SCHEMA)
        if not isinstance(schema, dict) or schema.get("$id") != "https://fth-skills.dev/contracts/system-design-state/1.0":
            errors.append("schema has unexpected $id")
    for path in paths:
        try:
            value = load(path)
        except Exception as exc:  # pragma: no cover - CLI diagnostic
            errors.append(f"{path}: {exc}")
            continue
        if path.name.endswith("patch.json") or path.name.endswith("handoff.json"):
            errors.extend(f"{path}: {error}" for error in validate_patch(value))
        else:
            errors.extend(f"{path}: {error}" for error in validate_state(value))
    if errors:
        print("CONTRACT VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"CONTRACT VALIDATION PASSED for {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
