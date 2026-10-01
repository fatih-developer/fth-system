#!/usr/bin/env python3
"""Acceptance checks for capacity model JSON (see references/estimate-units-v1.md)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from units import UnitError, check_estimate, is_number, parse_unit, to_base

SCENARIOS = ("baseline", "expected", "peak", "stress")
EST_STATUS = {"draft", "accepted", "superseded"}
CONFIDENCE = {"high", "medium", "low"}
EST_ID = re.compile(r"^EST-[0-9]{3,}$")
LINK_ID = re.compile(r"^(?:FR|NFR|ASM)-[0-9]{3,}$")
REQUIRED_OVERHEAD = ("index", "metadata", "replication")


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


def scenario_inputs(name: str, scenario: object, errors: list) -> dict:
    if not isinstance(scenario, dict):
        errors.append(f"scenario {name} must be an object")
        return {}
    if not text(scenario.get("window")):
        errors.append(f"scenario {name} needs a time window")
    inputs = scenario.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        errors.append(f"scenario {name} needs inputs with value and unit")
        return {}
    parsed: dict = {}
    for key, item in inputs.items():
        if not isinstance(item, dict) or not is_number(item.get("value")) or item["value"] < 0 or not isinstance(item.get("unit"), str):
            errors.append(f"scenario {name} input {key} needs a non-negative numeric value and unit")
            continue
        try:
            _, dims = parse_unit(item["unit"])
        except UnitError as exc:
            errors.append(f"scenario {name} input {key}: {exc}")
            continue
        parsed[key] = (to_base(item["value"], item["unit"]), dims)
    return parsed


def validate(model: object) -> list:
    if not isinstance(model, dict):
        return ["model must be an object"]
    errors: list = []
    if model.get("contract_version") != "1.0":
        errors.append("contract_version must be 1.0")
    scenarios = model.get("scenarios")
    if not isinstance(scenarios, dict) or set(scenarios) != set(SCENARIOS):
        errors.append(f"scenarios must be exactly {list(SCENARIOS)}")
        scenarios = scenarios if isinstance(scenarios, dict) else {}
    parsed = {name: scenario_inputs(name, scenarios[name], errors) for name in SCENARIOS if name in scenarios}
    names = [set(values) for values in parsed.values()]
    if names and any(item != names[0] for item in names):
        errors.append("every scenario must define the same input names so they can be compared")
    elif len(parsed) == len(SCENARIOS):
        for key in sorted(names[0]):
            series = [parsed[name][key] for name in SCENARIOS]
            if any(dims != series[0][1] for _, dims in series):
                errors.append(f"scenario input {key} changes dimension between scenarios")
            elif any(later[0] < earlier[0] for earlier, later in zip(series, series[1:])):
                errors.append(f"scenario input {key} must not decrease from baseline to expected to peak to stress")
    estimates = model.get("estimates")
    if not isinstance(estimates, list) or not estimates:
        errors.append("at least one estimate is required")
        estimates = []
    seen: set = set()
    covered: set = set()
    input_names: set = set()
    for index, estimate in enumerate(estimates):
        if not isinstance(estimate, dict):
            errors.append(f"estimate {index} must be an object")
            continue
        identifier = estimate.get("id")
        label = identifier if isinstance(identifier, str) else f"estimate {index}"
        if not isinstance(identifier, str) or not EST_ID.match(identifier):
            errors.append(f"{label} must have an EST-NNN id")
        elif identifier in seen:
            errors.append(f"duplicate estimate id {identifier}")
        seen.add(identifier)
        for field in ("horizon", "source"):
            if not text(estimate.get(field)):
                errors.append(f"{label} missing {field}")
        if estimate.get("status") not in EST_STATUS:
            errors.append(f"{label} status must be one of {sorted(EST_STATUS)}")
        if estimate.get("confidence") not in CONFIDENCE:
            errors.append(f"{label} confidence must be high, medium, or low")
        links = estimate.get("related_ids")
        if not isinstance(links, list) or not links or not all(isinstance(link, str) and LINK_ID.match(link) for link in links):
            errors.append(f"{label} must link to at least one FR-*, NFR-*, or ASM-* id")
        scenario = estimate.get("scenario")
        if scenario not in SCENARIOS:
            errors.append(f"{label} scenario must be one of {list(SCENARIOS)}")
        else:
            covered.add(scenario)
        errors.extend(f"{label}: {problem}" for problem in check_estimate(estimate))
        inputs = estimate.get("inputs") if isinstance(estimate.get("inputs"), dict) else {}
        input_names.update(inputs)
        for key, item in inputs.items():
            if scenario in parsed and key in parsed[scenario] and isinstance(item, dict) and is_number(item.get("value")):
                try:
                    value, dims = to_base(item["value"], item["unit"]), parse_unit(item["unit"])[1]
                except (UnitError, TypeError):
                    continue
                expected, expected_dims = parsed[scenario][key]
                if dims != expected_dims or abs(value - expected) > 1e-9 * max(1.0, abs(expected)):
                    errors.append(f"{label} input {key} disagrees with scenario {scenario}")
    for scenario in SCENARIOS:
        if scenario in parsed and scenario not in covered:
            errors.append(f"scenario {scenario} has no estimate")
    if not text(model.get("average_peak_distinction")):
        errors.append("average_peak_distinction is required")
    overhead = model.get("overhead_assumptions")
    if not isinstance(overhead, dict) or not overhead:
        errors.append("overhead_assumptions are required")
        overhead = {}
    for key in REQUIRED_OVERHEAD:
        if key not in overhead:
            errors.append(f"overhead_assumptions.{key} is required")
    for key, value in overhead.items():
        if not is_number(value) or value < 0:
            errors.append(f"overhead_assumptions.{key} must be a non-negative number")
    if is_number(overhead.get("replication")) and overhead["replication"] < 1:
        errors.append("overhead_assumptions.replication is a copy count and must be at least 1")
    sensitivity = model.get("sensitivity")
    if not isinstance(sensitivity, list) or len(sensitivity) < 3:
        errors.append("at least three sensitivity variables are required")
        sensitivity = []
    known = input_names | {key for values in parsed.values() for key in values} | set(overhead)
    variables, ranks = [], []
    for index, item in enumerate(sensitivity):
        if not isinstance(item, dict):
            errors.append(f"sensitivity[{index}] must be an object")
            continue
        variables.append(item.get("variable"))
        ranks.append(item.get("rank"))
        if item.get("variable") not in known:
            errors.append(f"sensitivity[{index}] variable {item.get('variable')!r} is not a model input or overhead")
        if item.get("impact") not in {"high", "medium", "low"}:
            errors.append(f"sensitivity[{index}] impact must be high, medium, or low")
    if len(set(map(str, variables))) != len(variables):
        errors.append("sensitivity variables must be distinct")
    if sensitivity and ranks != list(range(1, len(sensitivity) + 1)):
        errors.append("sensitivity must be ranked 1..N in order of outcome impact")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_capacity_model.py MODEL.json")
        return 2
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as handle:
            model = json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (OSError, ValueError) as exc:
        print(f"cannot read {sys.argv[1]}: {exc}")
        return 2
    errors = validate(model)
    if errors:
        print("CAPACITY ACCEPTANCE FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("CAPACITY ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
