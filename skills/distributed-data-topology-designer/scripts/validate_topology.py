#!/usr/bin/env python3
"""Acceptance checks for data topology decisions."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CONSISTENCY = {"strict_serializable", "serializable", "linearizable", "strong", "snapshot", "causal", "read_your_writes", "bounded_staleness", "eventual"}
WEAK = {"causal", "read_your_writes", "bounded_staleness", "eventual"}
LINK_ID = re.compile(r"^(?:FR|NFR|ASM|EST)-[0-9]{3,}$")
DEC_ID = re.compile(r"^DEC-[0-9]{3,}$")
ADVANCED = re.compile(r"micro-?services?|\bshard(?:s|ed|ing)?\b|\bpartition(?:s|ed|ing)?\b|\bkafka\b|event[ -]stream(?:ing)?|multi[- ]region|active[- ]active|polyglot|\breplica(?:s|ted|tion)?\b", re.I)
PATTERN_FIELDS = ("entity", "pattern", "operation_type", "volume", "index", "partition_key", "hotspot_risk")
OPERATION_FIELDS = ("operation", "entity", "invariant", "consistency", "transaction_boundary", "rpo", "rto")
DECISION_FIELDS = ("id", "topic", "choice", "rationale", "simpler_alternative", "tradeoff")
ADVANCED_FIELDS = ("rejection_reason", "operational_cost", "evolution_path")


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


def links_ok(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and LINK_ID.match(item) for item in value)


def objects(data: dict, field: str, errors: list) -> list:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        errors.append(f"{field} are required")
        return []
    if not all(isinstance(item, dict) for item in value):
        errors.append(f"{field} entries must be objects")
    return [item for item in value if isinstance(item, dict)]


def validate(data: object) -> list:
    if not isinstance(data, dict):
        return ["topology must be an object"]
    errors: list = []
    if data.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    patterns = objects(data, "access_patterns", errors)
    entities = set()
    for index, pattern in enumerate(patterns):
        label = f"access pattern {pattern.get('entity', index)}"
        for field in PATTERN_FIELDS:
            if not text(pattern.get(field)):
                errors.append(f"{label} missing {field}")
        if pattern.get("operation_type") not in {None, "read", "write", "read_write"} and text(pattern.get("operation_type")):
            errors.append(f"{label} operation_type must be read, write, or read_write")
        if not links_ok(pattern.get("related_ids")):
            errors.append(f"{label} must link to FR/NFR/ASM/EST evidence")
        if text(pattern.get("entity")):
            entities.add(pattern["entity"])
    if not text(data.get("hotspot_analysis")):
        errors.append("hotspot_analysis is required")
    operations = objects(data, "consistency_by_operation", errors)
    covered = set()
    for index, operation in enumerate(operations):
        label = f"consistency operation {operation.get('operation', index)}"
        for field in OPERATION_FIELDS:
            if not text(operation.get(field)):
                errors.append(f"{label} missing {field}")
        level = operation.get("consistency")
        if text(level) and level not in CONSISTENCY:
            errors.append(f"{label} consistency must be one of {sorted(CONSISTENCY)}")
        if level in WEAK:
            for field in ("conflict_strategy", "replication_lag"):
                if not text(operation.get(field)):
                    errors.append(f"{label} uses {level} consistency without {field}")
        if text(operation.get("entity")):
            if operation["entity"] not in entities:
                errors.append(f"{label} entity {operation['entity']} has no access pattern")
            covered.add(operation["entity"])
    for pattern in patterns:
        if pattern.get("operation_type") in {"write", "read_write"} and pattern.get("entity") not in covered:
            errors.append(f"written entity {pattern.get('entity')} has no operation-level consistency entry")
    decisions = data.get("decisions", [])
    if not isinstance(decisions, list) or not decisions:
        errors.append("at least one DEC-* trade-off decision is required")
        decisions = []
    seen = set()
    for index, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            errors.append(f"decision {index} must be an object")
            continue
        label = f"decision {decision.get('id', index)}"
        for field in DECISION_FIELDS:
            if not text(decision.get(field)):
                errors.append(f"{label} missing {field}")
        if text(decision.get("id")) and (not DEC_ID.match(decision["id"]) or decision["id"] in seen):
            errors.append(f"{label} must have a unique DEC-NNN id")
        seen.add(decision.get("id"))
        if not links_ok(decision.get("related_ids")):
            errors.append(f"{label} must link to FR/NFR/ASM/EST evidence")
        if ADVANCED.search(str(decision.get("choice", ""))):
            for field in ADVANCED_FIELDS:
                if not text(decision.get(field)):
                    errors.append(f"{label} is an advanced distribution decision without {field}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_topology.py TOPOLOGY.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(data)
    if errors:
        print("TOPOLOGY ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("TOPOLOGY ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
