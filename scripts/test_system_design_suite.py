#!/usr/bin/env python3
"""End-to-end regression checks for the system design skill suite.

Every acceptance script is exercised with its passing fixture and with
targeted mutations that must fail with a specific message, so a check that
silently stops firing breaks the suite.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "system-design" / "fixtures"
SKILLS = [
    "system-design-requirements-framer", "workload-capacity-modeler", "system-design-orchestrator",
    "distributed-data-topology-designer", "failure-mode-designer", "system-design-validator", "system-design-case-simulator",
]
SHARED_COPIES = [
    ("skills/system-design-validator/scripts/units.py", "skills/workload-capacity-modeler/scripts/units.py"),
    ("skills/system-design-validator/references/estimate-units-v1.md", "skills/workload-capacity-modeler/references/estimate-units-v1.md"),
]
SCENARIO_FIXTURES = ["low-traffic", "url-shortener-high-read", "ledger-transfer", "telemetry-ingestion", "negative-unit-error"]
CONTRACT_FIXTURES = SCENARIO_FIXTURES + ["validator-pass", "validator-negative", "validator-low-complexity", "orchestrator-incomplete", "generated-case", "requirements-framer-patch"]
CONTRACT = "scripts/validate_system_design_contract.py"
VALIDATOR = "skills/system-design-validator/scripts/validate_design.py"
CAPACITY = "skills/workload-capacity-modeler/scripts/validate_capacity_model.py"
REQUIREMENTS = "skills/system-design-requirements-framer/scripts/validate_requirements_patch.py"
ORCHESTRATOR = "skills/system-design-orchestrator/scripts/validate_orchestration.py"
TOPOLOGY = "skills/distributed-data-topology-designer/scripts/validate_topology.py"
FAILURE = "skills/failure-mode-designer/scripts/validate_failure_modes.py"
SIMULATOR = ROOT / "skills" / "system-design-case-simulator" / "scripts"

checks = 0


def run(command: list, expect: int = 0, contains: tuple = (), cwd: Path = ROOT) -> str:
    global checks
    result = subprocess.run([str(part) for part in command], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    output = result.stdout + result.stderr
    if result.returncode != expect:
        raise AssertionError(f"expected exit {expect}, got {result.returncode} for {' '.join(map(str, command))}\n{output}")
    for needle in contains:
        if needle not in output:
            raise AssertionError(f"expected {needle!r} in output of {' '.join(map(str, command))}\n{output}")
    checks += 1
    return output


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class Mutations:
    def __init__(self, directory: Path) -> None:
        self.directory, self.count = directory, 0

    def write(self, document: object) -> Path:
        self.count += 1
        path = self.directory / f"mutation-{self.count}.json"
        text = document if isinstance(document, str) else json.dumps(document)
        path.write_text(text, encoding="utf-8")
        return path

    def of(self, name: str, change: Callable[[dict], None]) -> Path:
        document = fixture(name)
        change(document)
        return self.write(document)


def expect_failures(script: str, base: str, banner: str, cases: list, mutations: Mutations) -> None:
    run([sys.executable, script, FIXTURES / f"{base}.json"])
    for change, message in cases:
        run([sys.executable, script, mutations.of(base, change)], expect=1, contains=(banner, message))


def setter(path: str, value: object) -> Callable[[dict], None]:
    def change(document: dict) -> None:
        *parents, last = path.split(".")
        node = document
        for part in parents:
            node = node[int(part)] if part.isdigit() else node[part]
        if value is DELETE:
            del node[int(last) if last.isdigit() else last]
        else:
            node[int(last) if last.isdigit() else last] = copy.deepcopy(value)
    return change


DELETE = object()


def check_layout() -> None:
    for name in SKILLS:
        directory = ROOT / "skills" / name
        for required in ("SKILL.md", "agents/openai.yaml", "references/contract-v1.md", "references/handoff-v1.md", "evals/evals.json"):
            assert (directory / required).is_file(), f"{name}: missing {required}"
    for left, right in SHARED_COPIES:
        assert (ROOT / left).read_bytes() == (ROOT / right).read_bytes(), f"shared copy drifted: {left} != {right}"
    manifest = json.loads((ROOT / "skills.sh.json").read_text(encoding="utf-8"))
    assert sorted(skill for group in manifest["groupings"] for skill in group["skills"]) == sorted(SKILLS)


def check_curated(temp: Path) -> None:
    run([sys.executable, "scripts/validate_curated_skills.py"])
    skill = "failure-mode-designer"
    mutations: list = [
        ("name mismatch", lambda root: replace(root / "skills" / skill / "SKILL.md", f"name: {skill}", "name: failure-designer"), "frontmatter name mismatch"),
        ("block scalar", lambda root: replace(root / "skills" / skill / "SKILL.md", "description: ", "description: >\n  "), "unsupported YAML construct"),
        ("duplicate key", lambda root: replace(root / "skills" / skill / "SKILL.md", "---\n\n#", "name: again\n---\n\n#"), "duplicate frontmatter key"),
        ("readme", lambda root: (root / "skills" / skill / "README.md").write_text("x", encoding="utf-8"), "is not allowed inside a skill folder"),
        ("orphan", lambda root: (root / "skills" / skill / "references" / "extra.md").write_text("x", encoding="utf-8"), "orphan file references/extra.md"),
        ("nested references", lambda root: (root / "skills" / skill / "references" / "deep").mkdir(), "must stay one level deep"),
        ("contract section", lambda root: replace(root / "skills" / skill / "references" / "contract-v1.md", "`FM-*`", "`FM`"), "omits ['FM-*']"),
        ("handoff field", lambda root: replace(root / "skills" / skill / "references" / "handoff-v1.md", "`remaining_risks`, ", ""), "omits ['remaining_risks']"),
        ("default prompt", lambda root: replace(root / "skills" / skill / "agents" / "openai.yaml", f"${skill}", "this skill"), "default_prompt must invoke"),
        ("no negative eval", lambda root: replace(root / "skills" / skill / "evals" / "evals.json", "Should", "Must", count=-1), "should-not-trigger"),
        ("missing reference", lambda root: replace(root / "skills" / skill / "SKILL.md", "scripts/validate_failure_modes.py", "scripts/missing.py"), "missing reference scripts/missing.py"),
        ("manifest", lambda root: replace(root / "skills.sh.json", '"failure-mode-designer",', ""), "manifest mismatch"),
        ("syntax error", lambda root: (root / "skills" / skill / "scripts" / "validate_failure_modes.py").write_text("#!/usr/bin/env python3\ndef (:\n", encoding="utf-8"), "does not compile"),
    ]
    for index, (_, mutate, message) in enumerate(mutations):
        root = temp / f"curated-{index}"
        shutil.copytree(ROOT / "skills", root / "skills", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "skills.sh.json", root / "skills.sh.json")
        mutate(root)
        run([sys.executable, root / "scripts" / "validate_curated_skills.py"], expect=1, contains=("VALIDATION FAILED", message), cwd=root)


def replace(path: Path, old: str, new: str, count: int = 1) -> None:
    content = path.read_text(encoding="utf-8")
    assert old in content, f"{old!r} not in {path}"
    path.write_text(content.replace(old, new, count), encoding="utf-8")


def check_contract(mutations: Mutations) -> None:
    run([sys.executable, CONTRACT, *[FIXTURES / f"{name}.json" for name in CONTRACT_FIXTURES]], contains=(f"PASSED for {len(CONTRACT_FIXTURES)} file(s)",))
    banner = "CONTRACT VALIDATION FAILED"
    state_cases = [
        (setter("design_id", "bad id"), "does not match ^SD-"),
        (setter("status", "whatever"), "$.status: must be one of"),
        (setter("mode", "demo"), "$.mode: must be one of"),
        (setter("functional_requirements.0.confidence", "banana"), "confidence: must be one of"),
        (setter("functional_requirements.0.id", "REQ-1"), "does not match ^FR-"),
        (setter("assumptions.0.status", "accepted"), "assumptions[0].status: must be one of"),
        (setter("assumptions.0.related_ids", ["FR-999"]), "references missing id FR-999"),
        (setter("assumptions.0.related_ids", ["ASM-001"]), "references itself"),
        (setter("assumptions.0.id", "FR-001"), "does not match ^ASM-"),
        (setter("problem", DELETE), "missing required field problem"),
        (setter("problem.actors", []), "needs at least 1 item"),
        (setter("contract_version", "1.1"), "must equal '1.0'"),
        (setter("traceability", [{"from": "FR-001", "to": ["DEC-404"], "relation": "satisfied_by"}]), "traceability[0] references missing id DEC-404"),
        (setter("completion_gates", {"validator": "DONE"}), "must be one of ['PASS'"),
        (setter("blocking_questions", ["a", "b", "c", "d"]), "allows at most 3"),
    ]
    for change, message in state_cases:
        run([sys.executable, CONTRACT, mutations.of("low-traffic", change)], expect=1, contains=(banner, message))
    duplicate = fixture("low-traffic")
    duplicate["functional_requirements"].append(dict(duplicate["functional_requirements"][0]))
    run([sys.executable, CONTRACT, mutations.write(duplicate)], expect=1, contains=("duplicate stable id: FR-001",))
    raw = (FIXTURES / "low-traffic.json").read_text(encoding="utf-8").replace('"mode": "production",', '"mode": "production", "mode": "interview",')
    run([sys.executable, CONTRACT, mutations.write(raw)], expect=1, contains=("duplicate JSON key: mode",))
    handoff_cases = [
        (setter("blocking_questions", ["a", "b", "c", "d"]), "allows at most 3"),
        (setter("extra", True), "$.extra: is not allowed"),
        (setter("state_patch.estimates_v2", []), "$.state_patch.estimates_v2: is not allowed"),
        (setter("handoff_summary", " "), "must be a non-empty string"),
        (setter("next_recommended_capability", "Workload Modeler"), "does not match"),
        (setter("state_patch.functional_requirements.0.id", "FR-1"), "does not match ^FR-"),
        (setter("validation_notes", DELETE), "missing required field validation_notes"),
    ]
    for change, message in handoff_cases:
        run([sys.executable, CONTRACT, mutations.of("requirements-framer-patch", change)], expect=1, contains=(banner, message))


def validator_output(path: Path, expect: str) -> dict:
    output = run([sys.executable, VALIDATOR, path, "--expect", expect], contains=(f"VALIDATOR DECISION: {expect}",))
    return json.loads(output[: output.rindex("}") + 1])


def check_validator(mutations: Mutations) -> None:
    passed = validator_output(FIXTURES / "validator-pass.json", "PASS")
    assert passed["findings"] == [], passed["findings"]
    assert passed["rules"] == dict({f"SD-R{index:03d}": "applied" for index in range(10)}, **{"SD-R004": "skipped: no advanced component or decision exists"}), passed["rules"]
    assert validator_output(FIXTURES / "validator-pass.json", "PASS") == passed, "validator output is not deterministic"
    conditional = validator_output(FIXTURES / "validator-low-complexity.json", "CONDITIONAL")
    assert [item["status"] for item in conditional["findings"]] == ["risk_accepted"]
    negative = validator_output(FIXTURES / "validator-negative.json", "FAIL")
    assert {item["id"] for item in negative["findings"]} == {"SDV-R003-EST-001"}, negative["findings"]
    unit_error = validator_output(FIXTURES / "negative-unit-error.json", "FAIL")
    assert {"SD-R003", "SD-R008"} <= {item["rule"] for item in unit_error["findings"]}
    for name in SCENARIO_FIXTURES:
        validator_output(FIXTURES / f"{name}.json", "FAIL")
    run([sys.executable, VALIDATOR, FIXTURES / "validator-pass.json", "--expect", "FAIL"], expect=1, contains=("EXPECTED FAIL BUT GOT PASS",))

    def unlink_fr2(state: dict) -> None:
        state["interfaces"] = [item for item in state["interfaces"] if "FR-002" not in item["related_ids"]]
        state["decisions"][0]["related_ids"].remove("FR-002")
        state["failure_modes"][0]["related_ids"].remove("FR-002")

    def kafka(state: dict) -> None:
        state["decisions"].append({"id": "DEC-002", "topic": "order events", "choice": "Kafka event streaming", "rationale": "future analytics", "related_ids": ["FR-001"], "status": "accepted", "source": "fixture", "confidence": "low"})

    def money(state: dict) -> None:
        state["functional_requirements"][0]["statement"] = "Staff can transfer balances between accounts"
        state["data_topology"]["consistency_by_operation"][0]["consistency"] = "eventual"
        del state["data_topology"]["consistency_by_operation"][0]["idempotency"]

    def conflict(state: dict) -> None:
        state["decisions"].append(dict(state["decisions"][0], id="DEC-002", choice="separate services per domain"))

    def critical_accepted(state: dict) -> None:
        state["estimates"][0]["value"] = 400
        state["validation_findings"].append({"id": "SDV-002", "rule": "SD-R003", "severity": "Critical", "related_ids": ["EST-001"], "status": "risk_accepted", "owner": "lead", "risk_acceptance": "ship anyway", "source": "fixture", "confidence": "high"})

    rule_cases = [
        ("SD-R000", setter("problem", DELETE), "missing top-level field problem"),
        ("SD-R000", setter("functional_requirements.1.id", "FR-001"), "duplicate stable ID FR-001"),
        ("SD-R001", unlink_fr2, "FR-002 is not linked"),
        ("SD-R002", setter("non_functional_requirements.0.window", DELETE), "missing window"),
        ("SD-R002", setter("non_functional_requirements.0.status", "needs_measurement"), "without a measurement_gap"),
        ("SD-R003", setter("estimates.0.value", 400), "formula evaluates to 40 KB/s but value is 400"),
        ("SD-R003", setter("estimates.0.unit", "events/s"), "formula yields"),
        ("SD-R003", setter("estimates.0.inputs.payload.unit", "kb/req"), "ambiguous unit 'kb'"),
        ("SD-R003", setter("estimates.0.formula", "peak_rate"), "declared inputs not used by formula"),
        ("SD-R003", setter("estimates.0.formula", "__import__('os')"), "unsupported formula syntax"),
        ("SD-R004", kafka, "DEC-002 (event_streaming) lacks complexity evidence"),
        ("SD-R004", setter("architecture.style", "sharded modular monolith"), "uses sharding without a DEC-* decision"),
        ("SD-R005", setter("data_topology.consistency_by_operation", []), "FR-001 changes state but has no operation invariant"),
        ("SD-R005", setter("data_topology.consistency_by_operation.0.transaction_boundary", ""), "missing transaction_boundary"),
        ("SD-R005", money, "is not strongly consistent"),
        ("SD-R006", setter("failure_modes.0.detection", ""), "FM-001 missing detection"),
        ("SD-R006", setter("failure_modes.0.dependency", "cache"), "dependency relational database has no FM"),
        ("SD-R007", setter("completion_gates.capacity", "PENDING"), "completion_gates.capacity PASS"),
        ("SD-R007", setter("validation_findings.0.status", "open"), "unresolved High finding SDV-001"),
        ("SD-R007", setter("blocking_questions", ["Who owns billing?"]), "open blocking questions"),
        ("SD-R007", critical_accepted, "cannot be risk-accepted"),
        ("SD-R003", critical_accepted, "value is 400"),
        ("SD-R008", conflict, "conflicting in-force decisions on topic 'architecture style'"),
        ("SD-R008", setter("decisions.0.topic", DELETE), "needs topic and choice"),
        ("SD-R009", setter("decisions.0.related_ids", ["FR-001", "EST-404"]), "references missing ID EST-404"),
        ("SD-R009", setter("estimates.0.inputs.peak_rate.source", "ASM-404"), "cites missing ID ASM-404"),
    ]
    for rule, change, message in rule_cases:
        result = validator_output(mutations.of("validator-pass", change), "FAIL")
        matching = [item for item in result["findings"] if item["rule"] == rule and message in item["evidence"]]
        assert matching, f"{rule} did not report {message!r}: {json.dumps(result['findings'], indent=2)}"
    accepted_wrong_rule = mutations.of("validator-low-complexity", setter("validation_findings.0.rule", "SD-R001"))
    validator_output(accepted_wrong_rule, "FAIL")
    accepted_no_owner = mutations.of("validator-low-complexity", setter("validation_findings.0.owner", ""))
    validator_output(accepted_no_owner, "FAIL")
    raw = (FIXTURES / "validator-pass.json").read_text(encoding="utf-8").replace('"status": "complete",', '"status": "complete", "status": "draft",')
    run([sys.executable, VALIDATOR, mutations.write(raw)], expect=2, contains=("duplicate JSON key: status",))


def check_capacity(mutations: Mutations) -> None:
    def drop_stress(model: dict) -> None:
        del model["scenarios"]["stress"]

    def literal_conversion(model: dict) -> None:
        model["estimates"][0]["formula"] = "request_rate * payload * 8"

    cases = [
        (drop_stress, "scenarios must be exactly"),
        (setter("scenarios.peak.inputs.request_rate.value", 20), "must not decrease"),
        (setter("scenarios.peak.window", ""), "scenario peak needs a time window"),
        (setter("scenarios.peak.inputs.request_rate.unit", "bytes"), "changes dimension between scenarios"),
        (setter("scenarios.peak.inputs.extra", {"value": 1, "unit": "s"}), "same input names"),
        (setter("estimates.0.value", 1), "formula evaluates to"),
        (literal_conversion, "numeric literals are dimensionless"),
        (setter("estimates.0.unit", "req/s"), "formula yields"),
        (setter("estimates.0.inputs.request_rate.value", 11), "disagrees with scenario baseline"),
        (setter("estimates.0.related_ids", ["DEC-001"]), "must link to at least one FR-*, NFR-*, or ASM-*"),
        (setter("estimates.0.scenario", "average"), "scenario must be one of"),
        (setter("estimates.3.scenario", "peak"), "scenario stress has no estimate"),
        (setter("estimates.1.id", "EST-001"), "duplicate estimate id EST-001"),
        (setter("estimates.0.confidence", "certain"), "confidence must be"),
        (setter("overhead_assumptions.replication", 0.5), "must be at least 1"),
        (setter("overhead_assumptions.metadata", DELETE), "overhead_assumptions.metadata is required"),
        (setter("sensitivity", [{"variable": "request_rate", "impact": "high", "rank": 1}]), "at least three sensitivity variables"),
        (setter("sensitivity.2.rank", 5), "ranked 1..N"),
        (setter("sensitivity.2.variable", "request_rate"), "must be distinct"),
        (setter("sensitivity.2.variable", "moon_phase"), "is not a model input"),
        (setter("average_peak_distinction", ""), "average_peak_distinction is required"),
    ]
    expect_failures(CAPACITY, "capacity-model", "CAPACITY ACCEPTANCE FAILED", cases, mutations)


def check_requirements(mutations: Mutations) -> None:
    cases = [
        (setter("blocking_questions", ["a", "b", "c", "d"]), "at most three"),
        (setter("state_patch.non_functional_requirements.0.unit", DELETE), "is not measurable (unit)"),
        (setter("state_patch.non_functional_requirements.0.target", "fast"), "numeric target"),
        (setter("state_patch.non_functional_requirements.0.status", "needs_measurement"), "without a measurement_gap"),
        (setter("state_patch.decisions", []), "state_patch.decisions is not owned"),
        (setter("unexpected", 1), "unknown field unexpected"),
        (setter("remaining_risks", DELETE), "envelope missing remaining_risks"),
        (setter("state_patch.functional_requirements.0.id", "FR-2"), "invalid stable id"),
        (setter("state_patch.functional_requirements.0.status", "done"), "status must be one of"),
        (setter("state_patch.functional_requirements.0.statement", ""), "needs a statement"),
        (setter("state_patch.assumptions.0.status", "accepted"), "status must be one of"),
        (setter("state_patch.assumptions.0.confidence", "high"), "inferred assumption presented with high confidence"),
        (setter("state_patch.assumptions.0.related_ids", ["ASM-002"]), "other than itself"),
        (setter("next_recommended_capability", ""), "must be a capability name"),
        (setter("contract_version", "2.0"), "contract_version must be 1.0"),
    ]
    expect_failures(REQUIREMENTS, "requirements-framer-patch", "REQUIREMENTS ACCEPTANCE FAILED", cases, mutations)


def check_orchestrator(mutations: Mutations) -> None:
    def advanced(state: dict) -> None:
        state["decisions"] = [{"id": "DEC-001", "topic": "services", "choice": "microservices per team", "rationale": "teams", "simpler_alternative": "modular monolith", "related_ids": ["FR-001"], "status": "accepted", "source": "fixture", "confidence": "low"}]

    cases = [
        (setter("status", "complete"), "complete state requires gate capacity PASS"),
        (setter("status", "complete"), "complete state has no failure modes"),
        (setter("status", "validated"), "validated state requires validator PASS"),
        (setter("completion_gates.validator", "PASS"), "gate validator cannot PASS before gate failure passes"),
        (setter("completion_gates.deploy", "PASS"), "unknown completion gate deploy"),
        (setter("completion_gates.capacity", "SKIPPED"), "completion gate capacity must be one of"),
        (setter("blocking_questions", ["a", "b", "c", "d"]), "blocking question budget exceeded"),
        (advanced, "advanced decision DEC-001 lacks rejection_reason"),
        (setter("assumptions.0.related_ids", ["NFR-404"]), "dangling or self reference NFR-404"),
        (setter("problem", DELETE), "missing top-level field problem"),
        (setter("design_id", "orders"), "design_id must match SD-*"),
    ]
    expect_failures(ORCHESTRATOR, "orchestrator-incomplete", "ORCHESTRATION ACCEPTANCE FAILED", cases, mutations)
    validated_with_open = fixture("validator-pass")
    validated_with_open["validation_findings"][0]["status"] = "open"
    run([sys.executable, ORCHESTRATOR, mutations.write(validated_with_open)], expect=1, contains=("contradicts unresolved findings",))
    production_owner = fixture("validator-pass")
    run([sys.executable, ORCHESTRATOR, mutations.write(production_owner)], expect=1, contains=("requires an owner on FM-001",))
    production_owner["failure_modes"][0]["owner"] = "orders on-call"
    run([sys.executable, ORCHESTRATOR, mutations.write(production_owner)], contains=("ORCHESTRATION ACCEPTANCE PASSED",))


def check_topology(mutations: Mutations) -> None:
    cases = [
        (setter("hotspot_analysis", ""), "hotspot_analysis is required"),
        (setter("access_patterns.0.partition_key", DELETE), "missing partition_key"),
        (setter("access_patterns.0.related_ids", []), "must link to FR/NFR/ASM/EST evidence"),
        (setter("consistency_by_operation.0.consistency", "eventual"), "without conflict_strategy"),
        (setter("consistency_by_operation.0.consistency", "mostly"), "consistency must be one of"),
        (setter("consistency_by_operation.0.entity", "account"), "written entity ledger_entry has no operation-level consistency entry"),
        (setter("consistency_by_operation.0.rto", ""), "missing rto"),
        (setter("decisions.0.choice", "shard ledger by account_id"), "without evolution_path"),
        (setter("decisions.0.id", "D1"), "unique DEC-NNN id"),
        (setter("decisions", []), "at least one DEC-* trade-off decision"),
    ]
    expect_failures(TOPOLOGY, "topology", "TOPOLOGY ACCEPTANCE FAILED", cases, mutations)


def check_failure_modes(mutations: Mutations) -> None:
    cases = [
        (setter("critical_flows", ["create_order", "read_order", "cancel_order"]), "critical flows without failure mode: ['cancel_order']"),
        (setter("failure_modes.0.critical_flows", ["ship_order"]), "unknown critical flow ship_order"),
        (setter("failure_modes.0.detection", "monitor the database"), "needs a measurable threshold"),
        (setter("failure_modes.0.owner", DELETE), "missing owner"),
        (setter("failure_modes.0.retry_policy.jitter", "none"), "must use jitter"),
        (setter("failure_modes.0.retry_policy.budget", "until success"), "bounded by a number"),
        (setter("failure_modes.0.retry_policy.backoff", "constant"), "must back off"),
        (setter("failure_modes.0.retry_policy.idempotency", DELETE), "unsafe retry policy"),
        (setter("failure_modes.1.retryable", "no"), "retryable must be true or false"),
        (setter("failure_modes.1.related_ids", ["ASM-001"]), "must tie recovery to at least one FR-* or NFR-*"),
        (setter("failure_modes.1.id", "FM-001"), "duplicate failure mode id FM-001"),
    ]
    expect_failures(FAILURE, "failure-model", "FAILURE ACCEPTANCE FAILED", cases, mutations)


def check_simulator(temp: Path, mutations: Mutations) -> None:
    generate, validate = SIMULATOR / "generate_case.py", SIMULATOR / "validate_case.py"
    regenerated = temp / "regenerated.json"
    run([sys.executable, generate, "--input", FIXTURES / "case-params.json", "--output", regenerated])
    assert regenerated.read_text(encoding="utf-8") == (FIXTURES / "generated-case.json").read_text(encoding="utf-8"), "generated-case.json is stale"
    cases = {}
    for name, params in {
        "base": {"domain": "orders", "mode": "interview", "variation": "baseline"},
        "high": {"domain": "orders", "request_rate": 50000, "mode": "production", "variation": "growth_shock", "consistency": "strong", "geography": "global", "compliance": ["GDPR"]},
    }.items():
        source, target = temp / f"{name}.json", temp / f"{name}-out.json"
        source.write_text(json.dumps(params), encoding="utf-8")
        run([sys.executable, generate, "--input", source, "--output", target])
        run([sys.executable, validate, target], contains=("SIMULATOR ACCEPTANCE PASSED",))
        run([sys.executable, CONTRACT, target])
        cases[name] = json.loads(target.read_text(encoding="utf-8"))
    low, high = cases["base"], cases["high"]
    assert len(high["decision_areas"]) > len(low["decision_areas"]) and low["mode"] == "interview" and high["mode"] == "production"
    assert [item["statement"] for item in low["assumptions"]] == ["request_rate defaults to 20 because it was not supplied"]
    assert len(low["open_questions"]) <= 3
    for params, message in (
        ({"domain": "orders", "mode": "interview"}, "missing required parameter variation"),
        ({"domain": "orders", "mode": "interview", "variation": "baseline", "request_rate": "fast"}, "request_rate must be"),
        ({"domain": "orders", "mode": "interview", "variation": "baseline", "request_rate": True}, "request_rate must be"),
        ({"domain": "orders", "mode": "interview", "variation": "baseline", "colour": "blue"}, "unknown parameter colour"),
        ({"domain": "space", "mode": "interview", "variation": "baseline"}, "domain must be one of"),
        ({"domain": "orders", "mode": "interview", "variation": "baseline", "availability": 100}, "availability must be"),
    ):
        source = temp / "invalid.json"
        source.write_text(json.dumps(params), encoding="utf-8")
        run([sys.executable, generate, "--input", source, "--output", temp / "unused.json"], expect=2, contains=("INVALID CASE PARAMETERS", message))
    banner = "SIMULATOR ACCEPTANCE FAILED"
    for change, message in (
        (setter("design_id", "SD-SIM-0000000000"), "does not match the parameters"),
        (setter("parameters.request_rate", 1), "does not match the parameters"),
        (setter("mode", "interview"), "mode does not match parameters"),
        (setter("decision_areas.0", "use Kafka for ingestion"), "prescribes a vendor (Kafka)"),
        (setter("decisions", [{"id": "DEC-001"}]), "decisions must be empty"),
        (setter("rubric.capacity", 30), "totalling 100"),
        (setter("variation.injected_change", "anything"), "variation does not match parameters"),
        (setter("status", "complete"), "must start as draft"),
    ):
        run([sys.executable, validate, mutations.of("generated-case", change)], expect=1, contains=(banner, message))
    interview = copy.deepcopy(low)
    interview["open_questions"] = ["a", "b", "c", "d"]
    run([sys.executable, validate, mutations.write(interview)], expect=1, contains=("at most 3 critical questions",))


def main() -> int:
    check_layout()
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        mutations = Mutations(temp)
        check_curated(temp)
        check_contract(mutations)
        check_validator(mutations)
        check_capacity(mutations)
        check_requirements(mutations)
        check_orchestrator(mutations)
        check_topology(mutations)
        check_failure_modes(mutations)
        check_simulator(temp, mutations)
    print(f"SYSTEM DESIGN SUITE REGRESSION PASSED ({checks} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
