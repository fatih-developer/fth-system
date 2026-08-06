#!/usr/bin/env python3
"""Validate skill frontmatter, discovery manifests, and local references."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = {"name", "description"}
PATH_REF_RE = re.compile(r"(?:references|templates|scripts|assets|agents)/[A-Za-z0-9._/-]+")


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter start")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing frontmatter end") from exc
    data: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "skills"
    skill_dirs = sorted(path.parent for path in root.rglob("SKILL.md"))
    errors: list[str] = []
    for skill_dir in skill_dirs:
        try:
            data = frontmatter(skill_dir / "SKILL.md")
        except ValueError as exc:
            errors.append(f"{skill_dir.name}: {exc}")
            continue
        if REQUIRED - data.keys():
            errors.append(f"{skill_dir.name}: missing {sorted(REQUIRED - data.keys())}")
        if data.get("name") != skill_dir.name:
            errors.append(f"{skill_dir.name}: frontmatter name mismatch")
        if not (skill_dir / "agents" / "openai.yaml").exists():
            errors.append(f"{skill_dir.name}: missing agents/openai.yaml")
        for reference in set(PATH_REF_RE.findall((skill_dir / "SKILL.md").read_text(encoding="utf-8"))):
            if not (skill_dir / reference.rstrip("`.,:;)]}")).exists():
                errors.append(f"{skill_dir.name}: missing reference {reference}")
    manifest = root.parent / "skills.sh.json"
    if not manifest.exists():
        errors.append("missing skills.sh.json")
    else:
        import json
        listed = [skill for group in json.loads(manifest.read_text(encoding="utf-8"))["groupings"] for skill in group["skills"]]
        actual = [path.name for path in skill_dirs]
        if sorted(listed) != sorted(actual):
            errors.append(f"manifest mismatch: listed={sorted(listed)} actual={sorted(actual)}")
    if errors:
        print("VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Validation PASSED for {len(skill_dirs)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
