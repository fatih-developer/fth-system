#!/usr/bin/env python3
"""Validate skill layout, frontmatter, discovery manifests, evals, and local contract references."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REQUIRED = {"name", "description"}
ALLOWED_FRONTMATTER = {"name", "description", "license", "compatibility", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PATH_REF_RE = re.compile(r"(?:references|templates|scripts|assets|agents|evals)/[A-Za-z0-9._/-]+")
ALLOWED_ENTRIES = {"SKILL.md", "agents", "references", "scripts", "evals", "assets", "templates"}
FORBIDDEN_RE = re.compile(r"^(?:readme|changelog|install(?:ation)?|contributing)(?:\.[a-z]+)?$", re.I)
ID_FAMILIES = ("FR-*", "NFR-*", "ASM-*", "EST-*", "DEC-*", "FM-*", "SDV-*")
CONTRACT_TERMS = ("1.0", "design_id", "SD-*", "mode", "status") + ID_FAMILIES
HANDOFF_FIELDS = ("contract_version", "state_patch", "handoff_summary", "blocking_questions", "remaining_risks", "next_recommended_capability", "validation_notes")
MAX_SKILL_LINES = 500


def _unquote(value: str, where: str) -> str:
    if value[:1] in {'"', "'"}:
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError(f"unterminated quoted value in {where}")
        inner = value[1:-1]
        return json.loads(value) if value[0] == '"' else inner.replace("''", "'")
    if value[:1] in {"|", ">", "[", "{", "&", "*", "!"}:
        raise ValueError(f"unsupported YAML construct in {where}: {value[:1]}")
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def frontmatter(path: Path) -> tuple:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing frontmatter start")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line == "---")
    except StopIteration as exc:
        raise ValueError("missing frontmatter end") from exc
    data: dict = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line[:1].isspace():
            raise ValueError(f"nested frontmatter is not supported: {line.strip()}")
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):(?: (.*))?", line)
        if not match:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, raw = match.group(1), (match.group(2) or "").strip()
        if key in data:
            raise ValueError(f"duplicate frontmatter key {key}")
        data[key] = _unquote(raw, f"frontmatter {key}")
    return data, lines[end + 1:]


def simple_yaml(path: Path) -> dict:
    """Parse the two-level mapping used by agents/openai.yaml."""
    data: dict = {}
    section = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top = re.fullmatch(r"([a-z_]+):\s*", line)
        child = re.fullmatch(r"  ([a-z_]+): (.+)", line)
        if top:
            section = top.group(1)
            if section in data:
                raise ValueError(f"line {number}: duplicate section {section}")
            data[section] = {}
        elif child and section:
            key = child.group(1)
            if key in data[section]:
                raise ValueError(f"line {number}: duplicate key {section}.{key}")
            raw = child.group(2).strip()
            data[section][key] = {"true": True, "false": False}.get(raw, None) if raw in {"true", "false"} else _unquote(raw, f"line {number}")
        else:
            raise ValueError(f"line {number}: unsupported YAML: {line.strip()}")
    return data


def check_agents(skill: Path, errors: list) -> None:
    path = skill / "agents" / "openai.yaml"
    if not path.exists():
        errors.append(f"{skill.name}: missing agents/openai.yaml")
        return
    try:
        data = simple_yaml(path)
    except ValueError as exc:
        errors.append(f"{skill.name}: agents/openai.yaml {exc}")
        return
    interface = data.get("interface", {})
    for key in ("display_name", "short_description", "default_prompt"):
        if not isinstance(interface.get(key), str) or not interface[key].strip():
            errors.append(f"{skill.name}: agents/openai.yaml interface.{key} is required")
    if f"${skill.name}" not in str(interface.get("default_prompt", "")):
        errors.append(f"{skill.name}: default_prompt must invoke ${skill.name}")
    if not isinstance(data.get("policy", {}).get("allow_implicit_invocation"), bool):
        errors.append(f"{skill.name}: policy.allow_implicit_invocation must be true or false")


def check_evals(skill: Path, errors: list) -> None:
    path = skill / "evals" / "evals.json"
    if not path.exists():
        errors.append(f"{skill.name}: missing evals/evals.json")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"{skill.name}: evals/evals.json is invalid JSON: {exc}")
        return
    if data.get("skill_name") != skill.name:
        errors.append(f"{skill.name}: evals skill_name mismatch")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{skill.name}: evals must be a non-empty list")
        return
    ids = [item.get("id") for item in evals if isinstance(item, dict)]
    if len(ids) != len(evals) or len(set(ids)) != len(ids) or not all(isinstance(i, int) for i in ids):
        errors.append(f"{skill.name}: eval ids must be unique integers")
    negatives = 0
    for item in evals:
        if not isinstance(item, dict):
            continue
        for key in ("prompt", "expected_output"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{skill.name}: eval {item.get('id')} missing {key}")
        expectations = item.get("expectations")
        if not isinstance(expectations, list) or not expectations or not all(isinstance(e, str) and e.strip() for e in expectations):
            errors.append(f"{skill.name}: eval {item.get('id')} needs expectations")
        if not isinstance(item.get("files"), list):
            errors.append(f"{skill.name}: eval {item.get('id')} files must be a list")
        if str(item.get("expected_output", "")).lower().startswith(("should not", "should defer")):
            negatives += 1
    if negatives == 0:
        errors.append(f"{skill.name}: evals need at least one should-not-trigger case")
    if negatives == len(evals):
        errors.append(f"{skill.name}: evals need at least one positive case")


def check_references(skill: Path, body: str, errors: list) -> None:
    referenced = set()
    for reference in PATH_REF_RE.findall(body):
        reference = reference.rstrip("`.,:;)]}")
        referenced.add(reference)
        if not (skill / reference).is_file():
            errors.append(f"{skill.name}: missing reference {reference}")
    for folder in ("references", "templates", "assets"):
        directory = skill / folder
        if directory.is_dir():
            for path in directory.iterdir():
                if path.is_dir():
                    errors.append(f"{skill.name}: {folder}/ must stay one level deep ({path.name}/)")
    reachable_text = body + "".join((skill / ref).read_text(encoding="utf-8") for ref in referenced if (skill / ref).is_file())
    for folder in ("references", "scripts"):
        directory = skill / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.name == "__pycache__":
                continue
            relative = f"{folder}/{path.name}"
            imported = path.suffix == ".py" and re.search(rf"^(?:from {re.escape(path.stem)} import|import {re.escape(path.stem)}\b)", reachable_text, re.M)
            if relative not in referenced and path.name not in reachable_text and not imported:
                errors.append(f"{skill.name}: orphan file {relative} is not referenced by SKILL.md")
    contract, handoff = skill / "references" / "contract-v1.md", skill / "references" / "handoff-v1.md"
    for path, terms in ((contract, CONTRACT_TERMS), (handoff, HANDOFF_FIELDS)):
        if not path.exists():
            errors.append(f"{skill.name}: missing references/{path.name}")
            continue
        content = path.read_text(encoding="utf-8")
        missing = [term for term in terms if term not in content]
        if missing:
            errors.append(f"{skill.name}: references/{path.name} omits {missing}")
    for path in (contract, handoff):
        if path.exists() and "contract-v1.0" in path.read_text(encoding="utf-8"):
            errors.append(f"{skill.name}: references/{path.name} uses the retired name contract-v1.0")


def check_scripts(skill: Path, errors: list) -> None:
    for path in sorted((skill / "scripts").glob("*.py")) if (skill / "scripts").is_dir() else []:
        source = path.read_text(encoding="utf-8")
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{skill.name}: scripts/{path.name} does not compile: {exc}")
        if not source.startswith("#!/usr/bin/env python3\n"):
            errors.append(f"{skill.name}: scripts/{path.name} needs a python3 shebang")


def check_skill(skill: Path, errors: list) -> None:
    try:
        data, body_lines = frontmatter(skill / "SKILL.md")
    except ValueError as exc:
        errors.append(f"{skill.name}: {exc}")
        return
    if REQUIRED - data.keys():
        errors.append(f"{skill.name}: missing {sorted(REQUIRED - data.keys())}")
    if set(data) - ALLOWED_FRONTMATTER:
        errors.append(f"{skill.name}: unsupported frontmatter keys {sorted(set(data) - ALLOWED_FRONTMATTER)}")
    name, description = data.get("name", ""), data.get("description", "")
    if name != skill.name:
        errors.append(f"{skill.name}: frontmatter name mismatch")
    if not NAME_RE.match(name) or len(name) > 64:
        errors.append(f"{skill.name}: name must be kebab-case and at most 64 characters")
    if not description or len(description) > 1024 or "<" in description or ">" in description:
        errors.append(f"{skill.name}: description must be 1-1024 characters without angle brackets")
    body = "\n".join(body_lines)
    if not body.strip():
        errors.append(f"{skill.name}: SKILL.md body is empty")
    if len(body_lines) > MAX_SKILL_LINES:
        errors.append(f"{skill.name}: SKILL.md exceeds {MAX_SKILL_LINES} lines; move detail into references/")
    for entry in sorted(skill.iterdir()):
        if entry.name not in ALLOWED_ENTRIES and entry.name != "__pycache__":
            errors.append(f"{skill.name}: unexpected entry {entry.name}")
    for path in skill.rglob("*"):
        if path.is_file() and FORBIDDEN_RE.match(path.name):
            errors.append(f"{skill.name}: {path.relative_to(skill)} is not allowed inside a skill folder")
    check_agents(skill, errors)
    check_evals(skill, errors)
    check_references(skill, body, errors)
    check_scripts(skill, errors)


def main() -> int:
    errors: list = []
    directories = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    skill_dirs = [path for path in directories if (path / "SKILL.md").is_file()]
    for path in directories:
        if path not in skill_dirs:
            errors.append(f"{path.name}: directory under skills/ has no SKILL.md")
    for nested in SKILLS.rglob("SKILL.md"):
        if nested.parent.parent != SKILLS:
            errors.append(f"{nested.relative_to(ROOT)}: skills must live directly under skills/")
    for skill in skill_dirs:
        check_skill(skill, errors)
    manifest = ROOT / "skills.sh.json"
    if not manifest.exists():
        errors.append("missing skills.sh.json")
    else:
        try:
            listed = [skill for group in json.loads(manifest.read_text(encoding="utf-8"))["groupings"] for skill in group["skills"]]
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"skills.sh.json is malformed: {exc}")
            listed = []
        actual = [path.name for path in skill_dirs]
        if len(set(listed)) != len(listed):
            errors.append("skills.sh.json lists a skill more than once")
        if sorted(set(listed)) != sorted(actual):
            errors.append(f"manifest mismatch: listed={sorted(set(listed))} actual={sorted(actual)}")
    if errors:
        print("VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Validation PASSED for {len(skill_dirs)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
