#!/usr/bin/env python3
"""Generate a deterministic, solution-neutral system-design case."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

DOMAINS = {"orders", "url_shortener", "ledger", "telemetry", "content"}
VARIATIONS = {
    "baseline": "none",
    "growth_shock": "request rate grows 10x",
    "dependency_outage": "primary dependency unavailable",
    "requirement_change": "retention or consistency requirement changes",
}
MODES = {"interview", "production"}
LEVELS = {"low", "medium", "high"}
DEFAULTS = {"request_rate": 20}
MAX_INTERVIEW_QUESTIONS = 3


def positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


PARAMETERS = {
    "domain": (lambda v: v in DOMAINS, f"one of {sorted(DOMAINS)}"),
    "mode": (lambda v: v in MODES, f"one of {sorted(MODES)}"),
    "variation": (lambda v: v in VARIATIONS, f"one of {sorted(VARIATIONS)}"),
    "request_rate": (positive_number, "a positive number of requests per second"),
    "users": (positive_int, "a positive integer"),
    "read_write_ratio": (lambda v: isinstance(v, str) and re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", v) is not None, "a ratio such as '100:1'"),
    "payload_bytes": (positive_int, "a positive integer"),
    "growth": (nonempty, "a non-empty description such as '2x/year'"),
    "retention_days": (positive_int, "a positive integer"),
    "consistency": (lambda v: v in {"eventual", "causal", "strong", "serializable"}, "one of eventual, causal, strong, serializable"),
    "availability": (lambda v: positive_number(v) and v < 100, "a percentage between 0 and 100, exclusive"),
    "latency_ms": (positive_number, "a positive number of milliseconds"),
    "geography": (lambda v: v in {"single_region", "multi_country", "global"}, "one of single_region, multi_country, global"),
    "compliance": (lambda v: isinstance(v, list) and all(nonempty(item) for item in v), "a list of regime names"),
    "team_maturity": (lambda v: v in LEVELS, "one of low, medium, high"),
    "budget": (lambda v: v in LEVELS, "one of low, medium, high"),
}
REQUIRED = ("domain", "mode", "variation")


def validate_params(params: object) -> list:
    if not isinstance(params, dict):
        return ["parameters must be a JSON object"]
    errors = [f"missing required parameter {name}" for name in REQUIRED if name not in params]
    errors += [f"unknown parameter {name}" for name in sorted(set(params) - set(PARAMETERS))]
    for name, value in params.items():
        if name in PARAMETERS and not PARAMETERS[name][0](value):
            errors.append(f"{name} must be {PARAMETERS[name][1]}")
    return errors


def case_id(params: dict) -> str:
    seed = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return "SD-SIM-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10].upper()


def generate(params: dict) -> dict:
    resolved = dict(DEFAULTS, **params)
    assumptions = [
        {"id": f"ASM-{index:03d}", "statement": f"{name} defaults to {DEFAULTS[name]} because it was not supplied", "status": "provisional", "source": "case simulator default", "confidence": "low"}
        for index, name in enumerate(sorted(set(DEFAULTS) - set(params)), 1)
    ]
    decision_areas = ["requirements and scope", "workload and capacity", "data topology and consistency", "failure recovery", "security and operations"]
    if resolved["request_rate"] >= 10000:
        decision_areas.append("partitioning or asynchronous processing")
    if resolved.get("consistency") in {"strong", "serializable"}:
        decision_areas.append("transaction boundaries and invariants")
    if resolved.get("geography") in {"multi_country", "global"}:
        decision_areas.append("data residency and geographic placement")
    if resolved.get("compliance"):
        decision_areas.append("compliance, audit, and deletion")
    if resolved["variation"] == "dependency_outage":
        decision_areas.append("dependency isolation and degraded mode")
    if resolved["variation"] == "requirement_change":
        decision_areas.append("change impact and data migration")
    questions = ["Which operations must never lose or duplicate data?", "What is the peak-to-average traffic ratio?", "Which failures may degrade service instead of failing it?"]
    if resolved["mode"] == "production":
        questions.append("Who owns on-call response and recovery targets?")
    return {
        "contract_version": "1.0", "design_id": case_id(params), "mode": resolved["mode"], "status": "draft",
        "problem": {"summary": f"Parametric {resolved['domain']} system-design case", "scope": "generated brief", "actors": ["end user", "operator"], "source": "case simulator", "confidence": "high"},
        "parameters": params, "variation": {"name": resolved["variation"], "injected_change": VARIATIONS[resolved["variation"]]},
        "functional_requirements": [], "non_functional_requirements": [], "constraints": [], "out_of_scope": [], "assumptions": assumptions, "estimates": [], "architecture": {}, "interfaces": [], "data_topology": {}, "decisions": [], "failure_modes": [], "validation_findings": [],
        "open_questions": questions[:MAX_INTERVIEW_QUESTIONS] if resolved["mode"] == "interview" else questions,
        "traceability": [],
        "decision_areas": decision_areas,
        "rubric": {"requirements": 20, "capacity": 20, "topology_consistency": 20, "failure_recovery": 20, "traceability_simplicity_operations": 20},
        "variation_catalog": sorted(VARIATIONS), "supported_modes": sorted(MODES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        with Path(args.input).open(encoding="utf-8") as handle:
            params = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"cannot read {args.input}: {exc}", file=sys.stderr)
        return 2
    errors = validate_params(params)
    if errors:
        print("INVALID CASE PARAMETERS", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 2
    with Path(args.output).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(generate(params), handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
