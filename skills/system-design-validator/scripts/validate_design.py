#!/usr/bin/env python3
"""Deterministic rule runner for rule catalog v1.0 (see references/rule-catalog-v1.md)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from units import check_estimate, is_number

CONTRACT_VERSION = "1.0"
REQUIRED_TOP_LEVEL = (
    "contract_version", "design_id", "mode", "status", "problem", "functional_requirements",
    "non_functional_requirements", "constraints", "out_of_scope", "assumptions", "estimates",
    "architecture", "interfaces", "data_topology", "decisions", "failure_modes",
    "validation_findings", "open_questions", "traceability",
)
COLLECTIONS = {
    "functional_requirements": "FR", "non_functional_requirements": "NFR", "assumptions": "ASM",
    "estimates": "EST", "decisions": "DEC", "failure_modes": "FM", "validation_findings": "SDV",
}
ID_RE = re.compile(r"^(?:FR|NFR|ASM|EST|DEC|FM)-[0-9]{3,}$|^SDV-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
ANY_ID_RE = re.compile(r"\b(?:FR|NFR|ASM|EST|DEC|FM)-[0-9]{3,}\b|\bSDV-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
CONFIDENCE = {"high", "medium", "low"}
STATUSES = {"draft", "in_progress", "validated", "complete", "blocked"}
INACTIVE = {"rejected", "deferred", "superseded", "out_of_scope", "invalidated"}
RESOLVED_FINDING = {"resolved", "risk_accepted"}
REQUIRED_GATES = ("requirements", "capacity", "topology", "failure", "validator")
ADVANCED = {
    "microservices": re.compile(r"micro-?services?", re.I),
    "sharding": re.compile(r"\bshard(?:s|ed|ing)?\b", re.I),
    "event_streaming": re.compile(r"\bkafka\b|\bkinesis\b|\bpulsar\b|event[ -]stream(?:ing)?", re.I),
    "multi_region": re.compile(r"multi[- ]region|active[- ]active|geo[- ]distributed", re.I),
    "polyglot": re.compile(r"polyglot", re.I),
}
COMPLEXITY_FIELDS = ("rationale", "simpler_alternative", "rejection_reason", "operational_cost", "evolution_path")
WRITE_RE = re.compile(r"\b(?:create[sd]?|update[sd]?|delete[sd]?|write[s]?|append[s]?|post[s]?|transfer[s]?|pay[s]?|debit[s]?|credit[s]?|book[s]?|reserve[s]?|submit[s]?|accept[s]?|ingest[s]?|store[s]?|insert[s]?|modif(?:y|ies)|cancel[s]?|record[s]?)\b", re.I)
MONEY_RE = re.compile(r"\b(?:ledger|transfer[s]?|payment[s]?|balance[s]?|money|debit[s]?|credit[s]?|refund[s]?|wallet[s]?)\b", re.I)
STRONG = {"strong", "linearizable", "serializable", "strict_serializable"}
REMEDIATION = {
    "SD-R000": "Repair the state so it conforms to contract v1.0 before re-running validation.",
    "SD-R001": "Link the requirement from a decision, interface, failure mode, or traceability entry.",
    "SD-R002": "Add metric, numeric target, unit, and window, or mark the NFR needs_measurement with a measurement_gap.",
    "SD-R003": "Declare named inputs with units, a formula over those names, and the declared value and unit.",
    "SD-R004": "Add rationale, simpler alternative, rejection reason, operational cost, evolution path, and measurable evidence IDs, or choose the simpler design.",
    "SD-R005": "Add a consistency_by_operation entry with invariant, consistency, transaction boundary, and related FR IDs.",
    "SD-R006": "Add an FM record with detection and recovery linked to the flow or dependency.",
    "SD-R007": "Satisfy every required phase gate and resolve open findings before asserting completion.",
    "SD-R008": "Supersede or reject one of the conflicting decisions and record the reason.",
    "SD-R009": "Point the reference at an existing stable ID or create the referenced record.",
}


class DuplicateKeyError(ValueError):
    pass


def _no_duplicates(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-standard JSON constant: {name}")


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def records(state: dict, collection: str) -> list:
    return [item for item in as_list(state.get(collection)) if isinstance(item, dict)]


def active(record: dict) -> bool:
    return record.get("status") not in INACTIVE


def related(record: dict) -> list:
    return [item for item in as_list(record.get("related_ids")) if isinstance(item, str)]


class Run:
    def __init__(self, state: dict) -> None:
        self.state = state
        self.findings: list = []
        self.rules: dict = {}
        self.notes: list = []

    def add(self, rule: str, severity: str, evidence: str, related_ids: list) -> None:
        self.findings.append({"rule": rule, "severity": severity, "evidence": evidence, "related_ids": sorted(set(related_ids))})

    def applied(self, rule: str) -> None:
        self.rules[rule] = "applied"

    def skipped(self, rule: str, reason: str) -> None:
        self.rules[rule] = f"skipped: {reason}"
        self.notes.append(f"{rule} skipped because {reason}")


def rule_contract(run: Run) -> bool:
    state, rule = run.state, "SD-R000"
    run.applied(rule)
    for field in REQUIRED_TOP_LEVEL:
        if field not in state:
            run.add(rule, "Critical", f"missing top-level field {field}", [])
    if state.get("contract_version") != CONTRACT_VERSION:
        run.add(rule, "Critical", "contract_version must be 1.0", [])
    if not (isinstance(state.get("design_id"), str) and re.fullmatch(r"SD-[A-Z0-9]+(?:-[A-Z0-9]+)*", state["design_id"])):
        run.add(rule, "Critical", "design_id must match SD-*", [])
    if state.get("mode") not in {"interview", "production"}:
        run.add(rule, "Critical", "mode must be interview or production", [])
    if state.get("status") not in STATUSES:
        run.add(rule, "Critical", f"status must be one of {sorted(STATUSES)}", [])
    seen: set = set()
    for collection, prefix in COLLECTIONS.items():
        value = state.get(collection, [])
        if not isinstance(value, list):
            run.add(rule, "Critical", f"{collection} must be an array", [])
            continue
        for index, record in enumerate(value):
            if not isinstance(record, dict):
                run.add(rule, "Critical", f"{collection}[{index}] must be an object", [])
                continue
            identifier = record.get("id")
            if not (isinstance(identifier, str) and ID_RE.match(identifier) and identifier.startswith(prefix + "-")):
                run.add(rule, "Critical", f"{collection}[{index}].id must be a {prefix}-* stable ID", [])
                continue
            if identifier in seen:
                run.add(rule, "Critical", f"duplicate stable ID {identifier}", [identifier])
            seen.add(identifier)
            for field in ("status", "source"):
                if not text(record.get(field)):
                    run.add(rule, "Critical", f"{identifier} missing {field}", [identifier])
            if record.get("confidence") not in CONFIDENCE:
                run.add(rule, "Critical", f"{identifier} confidence must be high, medium, or low", [identifier])
            if "related_ids" in record and not isinstance(record["related_ids"], list):
                run.add(rule, "Critical", f"{identifier} related_ids must be an array", [identifier])
    return not any(item["rule"] == rule for item in run.findings)


def all_ids(state: dict) -> set:
    return {record["id"] for collection in COLLECTIONS for record in records(state, collection) if isinstance(record.get("id"), str)}


def trace_edges(state: dict) -> list:
    edges = []
    for item in as_list(state.get("traceability")):
        if isinstance(item, dict):
            targets = item.get("to")
            for target in targets if isinstance(targets, list) else [targets]:
                edges.append((item.get("from"), target))
    return edges


def rule_references(run: Run) -> None:
    state, rule, known = run.state, "SD-R009", all_ids(run.state)
    run.applied(rule)
    for collection in COLLECTIONS:
        for record in records(state, collection):
            identifier = record.get("id")
            for reference in related(record):
                if reference == identifier:
                    run.add(rule, "Critical", f"{identifier} references itself", [identifier])
                elif reference not in known:
                    run.add(rule, "Critical", f"{identifier} references missing ID {reference}", [identifier])
            if collection == "estimates" and isinstance(record.get("inputs"), dict):
                for name, item in record["inputs"].items():
                    source = item.get("source") if isinstance(item, dict) else None
                    if isinstance(source, str) and ANY_ID_RE.fullmatch(source) and source not in known:
                        run.add(rule, "Critical", f"{identifier} input {name} cites missing ID {source}", [identifier])
    for index, item in enumerate(as_list(state.get("traceability"))):
        if not isinstance(item, dict) or not text(item.get("from")) or not item.get("to"):
            run.add(rule, "Critical", f"traceability[{index}] must have from and to", [])
    for source, target in trace_edges(state):
        for endpoint in (source, target):
            if isinstance(endpoint, str) and endpoint not in known:
                run.add(rule, "Critical", f"traceability references missing ID {endpoint}", [])


def rule_coverage(run: Run) -> None:
    state, rule = run.state, "SD-R001"
    requirements = [record for collection in ("functional_requirements", "non_functional_requirements") for record in records(state, collection) if active(record)]
    if not requirements:
        run.skipped(rule, "no in-force FR or NFR exists")
        return
    run.applied(rule)
    covered: set = set()
    for collection in ("decisions", "failure_modes"):
        for record in records(state, collection):
            if active(record):
                covered.update(related(record))
    for interface in as_list(state.get("interfaces")):
        if isinstance(interface, dict):
            covered.update(related(interface))
    for source, target in trace_edges(state):
        covered.update(endpoint for endpoint in (source, target) if isinstance(endpoint, str))
    for record in requirements:
        if record.get("id") not in covered:
            run.add(rule, "High", f"{record.get('id')} is not linked to any decision, interface, failure mode, or traceability entry", [str(record.get("id"))])


def rule_measurable(run: Run) -> None:
    rule = "SD-R002"
    nfrs = [record for record in records(run.state, "non_functional_requirements") if active(record)]
    if not nfrs:
        run.skipped(rule, "no in-force NFR exists")
        return
    run.applied(rule)
    for nfr in nfrs:
        identifier = str(nfr.get("id"))
        if nfr.get("status") == "needs_measurement":
            if not text(nfr.get("measurement_gap")):
                run.add(rule, "High", f"{identifier} is needs_measurement without a measurement_gap", [identifier])
            continue
        missing = [field for field in ("metric", "unit", "window") if not text(nfr.get(field))]
        if not is_number(nfr.get("target")):
            missing.append("numeric target")
        if missing:
            run.add(rule, "High", f"{identifier} is not measurable: missing {', '.join(missing)}", [identifier])


def rule_units(run: Run) -> None:
    rule = "SD-R003"
    estimates = [record for record in records(run.state, "estimates") if active(record)]
    if not estimates:
        run.skipped(rule, "no in-force EST exists")
        return
    run.applied(rule)
    for estimate in estimates:
        identifier = str(estimate.get("id"))
        for field in ("horizon",):
            if not text(estimate.get(field)):
                run.add(rule, "Critical", f"{identifier} missing {field}", [identifier])
        if not related(estimate):
            run.add(rule, "Critical", f"{identifier} has no related FR/NFR/ASM", [identifier])
        for problem in check_estimate(estimate):
            run.add(rule, "Critical", f"{identifier}: {problem}", [identifier])


def advanced_categories(value: object) -> set:
    found: set = set()
    if isinstance(value, str):
        found.update(name for name, pattern in ADVANCED.items() if pattern.search(value))
    elif isinstance(value, dict):
        for item in value.values():
            found |= advanced_categories(item)
    elif isinstance(value, list):
        for item in value:
            found |= advanced_categories(item)
    return found


def rule_complexity(run: Run) -> None:
    state, rule, known = run.state, "SD-R004", all_ids(run.state)
    decisions = [record for record in records(state, "decisions") if active(record)]
    in_design = advanced_categories(state.get("architecture")) | advanced_categories(state.get("data_topology"))
    advanced = [(record, advanced_categories(record.get("choice"))) for record in decisions]
    advanced = [(record, found) for record, found in advanced if found]
    if not advanced and not in_design:
        run.skipped(rule, "no advanced component or decision exists")
        return
    run.applied(rule)
    justified: set = set()
    for decision, found in advanced:
        identifier = str(decision.get("id"))
        missing = [field for field in COMPLEXITY_FIELDS if not text(decision.get(field))]
        evidence = [ref for ref in related(decision) if ref in known and ref.split("-")[0] in {"FR", "NFR", "ASM", "EST"}]
        if not evidence:
            missing.append("related FR/NFR/ASM/EST evidence")
        if missing:
            run.add(rule, "High", f"{identifier} ({', '.join(sorted(found))}) lacks complexity evidence: {', '.join(missing)}", [identifier])
        else:
            justified |= found
    for category in sorted(in_design - justified - {category for _, found in advanced for category in found}):
        run.add(rule, "High", f"architecture or data_topology uses {category} without a DEC-* decision", [])


def rule_consistency(run: Run) -> None:
    state, rule = run.state, "SD-R005"
    writers = [record for record in records(state, "functional_requirements") if active(record) and WRITE_RE.search(str(record.get("statement", "")))]
    topology = state.get("data_topology") if isinstance(state.get("data_topology"), dict) else {}
    operations = [item for item in as_list(topology.get("consistency_by_operation")) if isinstance(item, dict)]
    if not writers and not operations:
        run.skipped(rule, "no state-changing FR or write operation exists")
        return
    run.applied(rule)
    covered: dict = {}
    for index, operation in enumerate(operations):
        name = operation.get("operation") or f"consistency_by_operation[{index}]"
        missing = [field for field in ("operation", "invariant", "consistency", "transaction_boundary") if not text(operation.get(field))]
        if missing:
            run.add(rule, "Critical", f"operation {name} missing {', '.join(missing)}", related(operation))
        if not related(operation):
            run.add(rule, "Critical", f"operation {name} is not linked to any FR", [])
        for reference in related(operation):
            covered.setdefault(reference, []).append(operation)
    for requirement in writers:
        identifier = str(requirement.get("id"))
        linked = covered.get(identifier, [])
        if not linked:
            run.add(rule, "Critical", f"{identifier} changes state but has no operation invariant or transaction boundary", [identifier])
            continue
        if MONEY_RE.search(str(requirement.get("statement", ""))):
            for operation in linked:
                if str(operation.get("consistency", "")).lower() not in STRONG:
                    run.add(rule, "Critical", f"{identifier} moves value but operation {operation.get('operation')} is not strongly consistent", [identifier])
                if not text(operation.get("idempotency")):
                    run.add(rule, "Critical", f"{identifier} moves value but operation {operation.get('operation')} has no idempotency key", [identifier])


def dependency_names(state: dict) -> list:
    architecture = state.get("architecture") if isinstance(state.get("architecture"), dict) else {}
    names = []
    for item in as_list(architecture.get("dependencies")):
        name = item.get("name") if isinstance(item, dict) else item
        if text(name):
            names.append(name)
    return names


def rule_resilience(run: Run) -> None:
    state, rule = run.state, "SD-R006"
    flows = [record for record in records(state, "functional_requirements") if active(record)]
    exempt = [record for record in flows if record.get("critical") is False]
    flows = [record for record in flows if record.get("critical") is not False]
    dependencies = dependency_names(state)
    for record in exempt:
        run.notes.append(f"SD-R006 treats {record.get('id')} as non-critical because critical is false")
    if not flows and not dependencies:
        run.skipped(rule, "no critical flow or dependency exists")
        return
    run.applied(rule)
    failure_modes = [record for record in records(state, "failure_modes") if active(record)]
    covered_ids: set = set()
    covered_dependencies: set = set()
    for record in failure_modes:
        identifier = str(record.get("id"))
        missing = [field for field in ("detection", "recovery") if not text(record.get(field))]
        if missing:
            run.add(rule, "High", f"{identifier} missing {', '.join(missing)}", [identifier])
            continue
        covered_ids.update(related(record))
        if text(record.get("dependency")):
            covered_dependencies.add(record["dependency"])
    for flow in flows:
        if flow.get("id") not in covered_ids:
            run.add(rule, "High", f"critical flow {flow.get('id')} has no FM with detection and recovery", [str(flow.get("id"))])
    for name in dependencies:
        if name not in covered_dependencies:
            run.add(rule, "High", f"dependency {name} has no FM with detection and recovery", [])


def rule_conflicts(run: Run) -> None:
    rule = "SD-R008"
    decisions = [record for record in records(run.state, "decisions") if active(record)]
    if not decisions:
        run.skipped(rule, "no in-force DEC exists")
        return
    run.applied(rule)
    by_topic: dict = {}
    for decision in decisions:
        identifier = str(decision.get("id"))
        if not text(decision.get("topic")) or not text(decision.get("choice")):
            run.add(rule, "High", f"{identifier} needs topic and choice so conflicts can be detected", [identifier])
            continue
        by_topic.setdefault(decision["topic"].strip().lower(), []).append(decision)
    for topic, group in sorted(by_topic.items()):
        if len(group) < 2:
            continue
        ids = [str(item.get("id")) for item in group]
        choices = {str(item.get("choice")).strip().lower() for item in group}
        if len(choices) > 1:
            run.add(rule, "Critical", f"conflicting in-force decisions on topic '{topic}': {', '.join(ids)}", ids)
        else:
            run.add(rule, "High", f"duplicate decisions on topic '{topic}': {', '.join(ids)}", ids)


def rule_completion(run: Run) -> None:
    state, rule = run.state, "SD-R007"
    status = state.get("status")
    if status not in {"complete", "validated"}:
        run.skipped(rule, f"status is {status}")
        return
    run.applied(rule)
    gates = state.get("completion_gates") if isinstance(state.get("completion_gates"), dict) else {}
    if gates.get("validator") != "PASS":
        run.add(rule, "Critical", f"{status} status requires completion_gates.validator PASS", [])
    if status != "complete":
        return
    for gate in REQUIRED_GATES:
        if gate != "validator" and gates.get(gate) != "PASS":
            run.add(rule, "Critical", f"complete status requires completion_gates.{gate} PASS, got {gates.get(gate)!r}", [])
    if not records(state, "failure_modes"):
        run.add(rule, "Critical", "complete status requires failure modes", [])
    if not records(state, "validation_findings"):
        run.add(rule, "Critical", "complete status requires validation findings", [])
    for finding in records(state, "validation_findings"):
        if finding.get("severity") in {"Critical", "High"} and finding.get("status") not in RESOLVED_FINDING:
            run.add(rule, "Critical", f"complete status with unresolved {finding.get('severity')} finding {finding.get('id')}", [str(finding.get("id"))])
        if finding.get("severity") == "Critical" and finding.get("status") == "risk_accepted":
            run.add(rule, "Critical", f"Critical finding {finding.get('id')} cannot be risk-accepted", [str(finding.get("id"))])
    for nfr in records(state, "non_functional_requirements"):
        if nfr.get("status") == "needs_measurement":
            run.add(rule, "Critical", f"complete status with unmeasured {nfr.get('id')}", [str(nfr.get("id"))])
    if as_list(state.get("blocking_questions")):
        run.add(rule, "Critical", "complete status with open blocking questions", [])
    for question in as_list(state.get("open_questions")):
        if isinstance(question, dict) and question.get("blocking") is True and question.get("status") != "answered":
            run.add(rule, "Critical", f"complete status with blocking open question {question.get('id', question.get('question'))}", [])


def acceptance_for(finding: dict, accepted: list) -> dict | None:
    for record in accepted:
        if record.get("rule") == finding["rule"] and set(finding["related_ids"]) <= set(related(record)) and (finding["related_ids"] or not related(record)):
            return record
    return None


def assign_ids(findings: list) -> None:
    used: dict = {}
    for finding in findings:
        stem = "SDV-" + finding["rule"].split("-", 1)[1] + "-" + ("-".join(finding["related_ids"]) or "STATE")
        used[stem] = used.get(stem, 0) + 1
        finding["id"] = stem if used[stem] == 1 else f"{stem}-{used[stem]}"


def run_rules(state: object) -> dict:
    if not isinstance(state, dict):
        state = {}
    run = Run(state)
    contract_ok = rule_contract(run)
    if contract_ok:
        for check in (rule_references, rule_coverage, rule_measurable, rule_units, rule_complexity, rule_consistency, rule_resilience, rule_conflicts, rule_completion):
            check(run)
    else:
        run.notes.append("SD-R001..SD-R009 not evaluated because the state does not conform to contract v1.0")
    accepted = [record for record in records(state, "validation_findings") if record.get("status") == "risk_accepted" and text(record.get("owner")) and text(record.get("risk_acceptance"))]
    owner = state.get("owner") if text(state.get("owner")) else "unassigned"
    unaccepted_high = False
    for finding in run.findings:
        finding["remediation"] = REMEDIATION[finding["rule"]]
        acceptance = acceptance_for(finding, accepted) if finding["severity"] == "High" else None
        if acceptance:
            finding["status"], finding["owner"] = "risk_accepted", acceptance["owner"]
            finding["accepted_by"] = acceptance["id"]
        else:
            finding["status"], finding["owner"] = "open", owner
            unaccepted_high = unaccepted_high or finding["severity"] == "High"
    assign_ids(run.findings)
    if any(item["severity"] == "Critical" for item in run.findings) or unaccepted_high:
        decision = "FAIL"
    elif run.findings:
        decision = "CONDITIONAL"
    else:
        decision = "PASS"
    return {"contract_version": CONTRACT_VERSION, "decision": decision, "findings": run.findings, "rules": run.rules, "validation_notes": run.notes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design")
    parser.add_argument("--expect", choices=["PASS", "CONDITIONAL", "FAIL"])
    args = parser.parse_args()
    try:
        state = load_json(Path(args.design))
    except (OSError, ValueError) as exc:
        print(f"cannot read {args.design}: {exc}")
        return 2
    result = run_rules(state)
    print(json.dumps(result, indent=2))
    if args.expect and args.expect != result["decision"]:
        print(f"EXPECTED {args.expect} BUT GOT {result['decision']}")
        return 1
    print(f"VALIDATOR DECISION: {result['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
