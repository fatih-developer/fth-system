#!/usr/bin/env python3
"""Generate a deterministic, solution-neutral system-design case."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DOMAINS = {"orders", "url_shortener", "ledger", "telemetry", "content"}
VARIATIONS = {"baseline", "growth_shock", "dependency_outage", "requirement_change"}


def generate(params: dict[str, object]) -> dict[str, object]:
    domain = str(params.get("domain", "orders"))
    variation = str(params.get("variation", "baseline"))
    mode = str(params.get("mode", "interview"))
    seed = json.dumps(params, sort_keys=True, separators=(",", ":"))
    suffix = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10].upper()
    rate = params.get("request_rate", 20)
    changed = {"baseline": "none", "growth_shock": "request rate grows 10x", "dependency_outage": "primary dependency unavailable", "requirement_change": "retention or consistency requirement changes"}[variation]
    decision_areas = ["requirements and scope", "workload and capacity", "data topology and consistency", "failure recovery", "security and operations"]
    if float(rate) >= 10000:
        decision_areas.append("partitioning or asynchronous processing")
    if params.get("consistency") in {"strong", "serializable"}:
        decision_areas.append("transaction boundaries and invariants")
    return {
        "contract_version": "1.0", "design_id": f"SD-SIM-{suffix}", "mode": mode, "status": "draft",
        "problem": {"summary": f"Parametric {domain} system-design case", "scope": "generated brief", "actors": ["end user", "operator"], "source": "case simulator", "confidence": "high"},
        "parameters": params, "variation": {"name": variation, "injected_change": changed},
        "functional_requirements": [], "non_functional_requirements": [], "constraints": [], "out_of_scope": [], "assumptions": [], "estimates": [], "architecture": {}, "interfaces": [], "data_topology": {}, "decisions": [], "failure_modes": [], "validation_findings": [], "open_questions": [], "traceability": [],
        "decision_areas": decision_areas,
        "rubric": {"requirements": 20, "capacity": 20, "topology_consistency": 20, "failure_recovery": 20, "traceability_simplicity_operations": 20},
        "variation_catalog": sorted(VARIATIONS), "supported_modes": ["interview", "production"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with Path(args.input).open(encoding="utf-8") as handle:
        params = json.load(handle)
    if params.get("domain") not in DOMAINS or params.get("variation") not in VARIATIONS or params.get("mode") not in {"interview", "production"}:
        raise SystemExit("invalid domain, variation, or mode")
    with Path(args.output).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(generate(params), handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
