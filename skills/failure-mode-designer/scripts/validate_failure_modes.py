#!/usr/bin/env python3
"""Acceptance checks for failure-mode records."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FM_ID = re.compile(r"^FM-[0-9]{3,}$")
LINK_ID = re.compile(r"^(?:FR|NFR)-[0-9]{3,}$")
REQUIRED = ("trigger", "blast_radius", "detection", "mitigation", "degraded_mode", "recovery", "data_impact", "owner", "test_scenario")
RETRY_KEYS = ("backoff", "jitter", "budget", "idempotency", "retryable_errors")


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


def validate(data: object) -> list:
    if not isinstance(data, dict):
        return ["failure model must be an object"]
    errors: list = []
    if data.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    flows = data.get("critical_flows")
    if not isinstance(flows, list) or not flows or not all(text(flow) for flow in flows):
        errors.append("critical_flows must be a non-empty list of flow names")
        flows = []
    if len(set(flows)) != len(flows):
        errors.append("critical_flows must be unique")
    records = data.get("failure_modes")
    if not isinstance(records, list) or not records:
        errors.append("failure_modes are required")
        records = []
    covered, seen = set(), set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"failure mode {index} must be an object")
            continue
        identifier = record.get("id")
        label = identifier if isinstance(identifier, str) else f"failure mode {index}"
        if not isinstance(identifier, str) or not FM_ID.match(identifier):
            errors.append(f"{label} has invalid ID")
        elif identifier in seen:
            errors.append(f"duplicate failure mode id {identifier}")
        seen.add(identifier)
        for field in REQUIRED:
            if not text(record.get(field)):
                errors.append(f"{label} missing {field}")
        if text(record.get("detection")) and not re.search(r"\d", record["detection"]):
            errors.append(f"{label} detection needs a measurable threshold")
        record_flows = record.get("critical_flows")
        if not isinstance(record_flows, list) or not record_flows:
            errors.append(f"{label} must name the critical flows it affects")
            record_flows = []
        for flow in record_flows:
            if flow not in flows:
                errors.append(f"{label} references unknown critical flow {flow}")
        covered.update(flow for flow in record_flows if isinstance(flow, str))
        links = record.get("related_ids")
        if not isinstance(links, list) or not any(isinstance(link, str) and LINK_ID.match(link) for link in links):
            errors.append(f"{label} must tie recovery to at least one FR-* or NFR-*")
        retryable = record.get("retryable")
        if not isinstance(retryable, bool):
            errors.append(f"{label} retryable must be true or false")
        elif retryable:
            policy = record.get("retry_policy")
            if not isinstance(policy, dict) or not all(text(policy.get(key)) or (key == "retryable_errors" and isinstance(policy.get(key), list) and policy.get(key)) for key in RETRY_KEYS):
                errors.append(f"{label} has unsafe retry policy (needs {', '.join(RETRY_KEYS)})")
            else:
                if not re.search(r"\d", policy["budget"]):
                    errors.append(f"{label} retry budget must be bounded by a number")
                if policy["jitter"].strip().lower() in {"none", "no", "false", "off"}:
                    errors.append(f"{label} retry policy must use jitter")
                if policy["backoff"].strip().lower() in {"none", "constant", "fixed", "immediate"}:
                    errors.append(f"{label} retry policy must back off")
    missing = sorted(set(flows) - covered)
    if missing:
        errors.append(f"critical flows without failure mode: {missing}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_failure_modes.py FAILURE_MODEL.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(data)
    if errors:
        print("FAILURE ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("FAILURE ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
