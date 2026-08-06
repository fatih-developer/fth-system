# AGENTS.md — fth-system

This repository is the public System Design skill suite for the `skills.sh` ecosystem.

## Skill discovery requirements

Every skill must contain:

```text
skills/<skill-name>/SKILL.md
skills/<skill-name>/agents/openai.yaml
```

`SKILL.md` frontmatter must contain `name` and `description`, and `name` must exactly match the skill folder.

## Contract requirements

The suite uses system design contract and handoff version `1.0`. Do not create a callable `system-design-core-contract` skill. Each specialist carries the contract sections it needs in its own `references/` directory.

Stable ID families are `FR-*`, `NFR-*`, `ASM-*`, `EST-*`, `DEC-*`, `FM-*`, and `SDV-*`.

## Validation

Run these before committing:

```bash
python scripts/validate_curated_skills.py
python scripts/validate_system_design_contract.py tests/system-design/fixtures/low-traffic.json
python scripts/test_system_design_suite.py
```

Do not add README files, changelogs, or installation guides inside individual skill folders. Keep reusable detail in one-level `references/` files.
