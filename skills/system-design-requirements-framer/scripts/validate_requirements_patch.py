#!/usr/bin/env python3
"""Acceptance checks for a requirements-framer handoff envelope."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ENVELOPE = ("contract_version", "state_patch", "handoff_summary", "blocking_questions", "remaining_risks", "next_recommended_capability", "validation_notes")
OWNED = {"problem", "functional_requirements", "non_functional_requirements", "constraints", "out_of_scope", "assumptions", "open_questions", "traceability", "contract_version", "design_id", "mode", "status"}
FAMILIES = {
    "functional_requirements": ("FR", {"draft", "proposed", "accepted", "rejected", "deferred", "superseded"}),
    "non_functional_requirements": ("NFR", {"draft", "proposed", "accepted", "needs_measurement", "rejected", "deferred", "superseded"}),
    "assumptions": ("ASM", {"provisional", "validated", "invalidated"}),
}
CONFIDENCE = {"high", "medium", "low"}
ID_RE = re.compile(r"^(?:FR|NFR|ASM|EST|DEC|FM)-[0-9]{3,}$")


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


def string_list(value: object) -> bool:
    return isinstance(value, list) and all(text(item) for item in value)


def validate(envelope: object) -> list:
    if not isinstance(envelope, dict):
        return ["envelope must be an object"]
    errors: list = [f"envelope missing {field}" for field in ENVELOPE if field not in envelope]
    errors += [f"envelope has unknown field {field}" for field in sorted(set(envelope) - set(ENVELOPE))]
    if envelope.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    if not text(envelope.get("handoff_summary")):
        errors.append("handoff_summary must be a non-empty string")
    if not text(envelope.get("next_recommended_capability")) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", envelope.get("next_recommended_capability", "")):
        errors.append("next_recommended_capability must be a capability name")
    for field in ("remaining_risks", "validation_notes"):
        if not string_list(envelope.get(field)):
            errors.append(f"{field} must be a list of non-empty strings")
    questions = envelope.get("blocking_questions")
    if not string_list(questions) or len(questions) > 3:
        errors.append("blocking_questions must contain at most three non-empty strings")
    patch = envelope.get("state_patch")
    if not isinstance(patch, dict) or not patch:
        return errors + ["state_patch must be a non-empty object"]
    errors += [f"state_patch.{field} is not owned by the requirements framer" for field in sorted(set(patch) - OWNED)]
    if "contract_version" in patch and patch["contract_version"] != "1.0":
        errors.append("state_patch contract_version must be 1.0")
    if "problem" in patch:
        problem = patch["problem"]
        if not isinstance(problem, dict) or not all(text(problem.get(field)) for field in ("summary", "scope", "source")) or not string_list(problem.get("actors")) or not problem.get("actors"):
            errors.append("problem needs summary, scope, source, and at least one actor")
    seen: set = set()
    for collection, (prefix, statuses) in FAMILIES.items():
        value = patch.get(collection, [])
        if not isinstance(value, list):
            errors.append(f"{collection} must be an array")
            continue
        for index, record in enumerate(value):
            label = f"{collection}[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{label} must be an object")
                continue
            identifier = record.get("id")
            if not isinstance(identifier, str) or not re.fullmatch(prefix + r"-[0-9]{3,}", identifier):
                errors.append(f"{label} has invalid stable id (expected {prefix}-NNN)")
            elif identifier in seen:
                errors.append(f"duplicate stable id {identifier}")
            seen.add(identifier)
            label = identifier if isinstance(identifier, str) else label
            if not text(record.get("statement")):
                errors.append(f"{label} needs a statement")
            if not text(record.get("source")):
                errors.append(f"{label} lacks source")
            if record.get("confidence") not in CONFIDENCE:
                errors.append(f"{label} confidence must be high, medium, or low")
            if record.get("status") not in statuses:
                errors.append(f"{label} status must be one of {sorted(statuses)}")
            links = record.get("related_ids", [])
            if not isinstance(links, list) or not all(isinstance(link, str) and ID_RE.match(link) for link in links) or identifier in links:
                errors.append(f"{label} related_ids must be stable IDs other than itself")
            if collection == "non_functional_requirements":
                if record.get("status") == "needs_measurement":
                    if not text(record.get("measurement_gap")):
                        errors.append(f"{label} is needs_measurement without a measurement_gap")
                else:
                    missing = [field for field in ("metric", "unit", "window") if not text(record.get(field))]
                    target = record.get("target")
                    if not (isinstance(target, (int, float)) and not isinstance(target, bool) and math.isfinite(target)):
                        missing.append("numeric target")
                    if missing:
                        errors.append(f"NFR {label} is not measurable ({', '.join(missing)}) and is not marked needs_measurement")
            if collection == "assumptions" and record.get("confidence") == "high" and record.get("source") in {"inference", "assumption"}:
                errors.append(f"{label} is an inferred assumption presented with high confidence")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_requirements_patch.py PATCH.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            envelope = json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(envelope)
    if errors:
        print("REQUIREMENTS ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("REQUIREMENTS ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
