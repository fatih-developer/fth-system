#!/usr/bin/env python3
"""End-to-end regression checks for the system design skill suite."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    "system-design-requirements-framer", "workload-capacity-modeler", "system-design-orchestrator",
    "distributed-data-topology-designer", "failure-mode-designer", "system-design-validator", "system-design-case-simulator",
]


def run(command: list[str], expect: int = 0) -> str:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != expect:
        raise AssertionError(f"unexpected exit {result.returncode} for {' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main() -> int:
    for name in SKILLS:
        directory = ROOT / "skills" / name
        assert (directory / "SKILL.md").exists(), name
        assert (directory / "agents" / "openai.yaml").exists(), name
        assert (directory / "references" / "contract-v1.md").exists(), name
        assert (directory / "references" / "handoff-v1.md").exists(), name
        assert "contract-v1.0" not in (directory / "references" / "contract-v1.md").read_text(encoding="utf-8")
        contract = (directory / "references" / "contract-v1.md").read_text(encoding="utf-8")
        assert "1.0" in contract and "FR-*" in contract and "SDV-*" in contract
    run([sys.executable, "scripts/validate_curated_skills.py"])
    fixture_dir = ROOT / "tests" / "system-design" / "fixtures"
    state_fixtures = [fixture_dir / name for name in ("low-traffic.json", "url-shortener-high-read.json", "ledger-transfer.json", "telemetry-ingestion.json", "negative-unit-error.json")]
    run([sys.executable, "scripts/validate_system_design_contract.py", *map(str, state_fixtures)])
    run([sys.executable, "skills/system-design-requirements-framer/scripts/validate_requirements_patch.py", str(fixture_dir / "requirements-framer-patch.json")])
    run([sys.executable, "skills/workload-capacity-modeler/scripts/validate_capacity_model.py", str(fixture_dir / "capacity-model.json")])
    run([sys.executable, "skills/system-design-orchestrator/scripts/validate_orchestration.py", str(fixture_dir / "orchestrator-incomplete.json")])
    run([sys.executable, "skills/distributed-data-topology-designer/scripts/validate_topology.py", str(fixture_dir / "topology.json")])
    run([sys.executable, "skills/failure-mode-designer/scripts/validate_failure_modes.py", str(fixture_dir / "failure-model.json")])
    validator = ROOT / "skills" / "system-design-validator" / "scripts" / "validate_design.py"
    assert '"decision": "FAIL"' in run([sys.executable, str(validator), str(fixture_dir / "validator-negative.json")])
    assert '"decision": "CONDITIONAL"' in run([sys.executable, str(validator), str(fixture_dir / "validator-low-complexity.json")])
    assert '"decision": "PASS"' in run([sys.executable, str(validator), str(fixture_dir / "validator-pass.json")])
    simulator = ROOT / "skills" / "system-design-case-simulator" / "scripts"
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        base = {"domain": "orders", "request_rate": 20, "mode": "interview", "variation": "baseline"}
        high = {"domain": "orders", "request_rate": 50000, "mode": "production", "variation": "growth_shock"}
        base_input, high_input = temp_path / "base.json", temp_path / "high.json"
        base_input.write_text(json.dumps(base), encoding="utf-8")
        high_input.write_text(json.dumps(high), encoding="utf-8")
        base_output, high_output = temp_path / "base-out.json", temp_path / "high-out.json"
        run([sys.executable, str(simulator / "generate_case.py"), "--input", str(base_input), "--output", str(base_output)])
        run([sys.executable, str(simulator / "generate_case.py"), "--input", str(high_input), "--output", str(high_output)])
        run([sys.executable, str(simulator / "validate_case.py"), str(base_output)])
        run([sys.executable, str(simulator / "validate_case.py"), str(high_output)])
        low_case, high_case = json.loads(base_output.read_text()), json.loads(high_output.read_text())
        assert len(high_case["decision_areas"]) > len(low_case["decision_areas"])
        assert low_case["mode"] == "interview" and high_case["mode"] == "production"
    invalid_complete = json.loads((fixture_dir / "orchestrator-incomplete.json").read_text(encoding="utf-8"))
    invalid_complete["status"] = "complete"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(invalid_complete, handle)
        invalid_path = handle.name
    try:
        run([sys.executable, "skills/system-design-orchestrator/scripts/validate_orchestration.py", invalid_path], expect=1)
    finally:
        Path(invalid_path).unlink(missing_ok=True)
    print("SYSTEM DESIGN SUITE REGRESSION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
