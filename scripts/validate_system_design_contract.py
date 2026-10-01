#!/usr/bin/env python3
"""Validate system-design states and handoff envelopes against contract v1.0.

The JSON Schemas in tests/system-design/ are enforced with a small,
dependency-free engine that implements the subset of draft 2020-12 the
schemas use. An unsupported keyword is a schema error, never silently
ignored. Semantic checks the schema cannot express (unique stable IDs,
dangling references) run afterwards.

A document containing ``state_patch`` is validated as a handoff envelope;
anything else is validated as a full ``system_design_state``.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "tests" / "system-design"
STATE_SCHEMA = SCHEMA_DIR / "contract-schema.json"
HANDOFF_SCHEMA = SCHEMA_DIR / "handoff-schema.json"
SCHEMA_IDS = {
    STATE_SCHEMA: "https://fth-skills.dev/contracts/system-design-state/1.0",
    HANDOFF_SCHEMA: "https://fth-skills.dev/contracts/system-design-handoff/1.0",
}
COLLECTIONS = ("functional_requirements", "non_functional_requirements", "assumptions", "estimates", "decisions", "failure_modes", "validation_findings")
ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs"}
KEYWORDS = {
    "type", "required", "properties", "additionalProperties", "items", "enum", "const", "pattern",
    "minLength", "minItems", "maxItems", "uniqueItems", "minProperties", "$ref", "allOf", "anyOf",
}


class SchemaError(Exception):
    """The schema itself is invalid or uses an unsupported keyword."""


def _no_duplicates(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-standard JSON constant: {name}")


def load(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)


def _is_type(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    raise SchemaError(f"unknown type {expected}")


class Validator:
    def __init__(self, schema: dict) -> None:
        self.root = schema

    def resolve(self, reference: str) -> dict:
        if not reference.startswith("#/"):
            raise SchemaError(f"only local $ref is supported: {reference}")
        node: object = self.root
        for part in reference[2:].split("/"):
            if not isinstance(node, dict) or part not in node:
                raise SchemaError(f"unresolvable $ref {reference}")
            node = node[part]
        if not isinstance(node, dict):
            raise SchemaError(f"$ref {reference} is not a schema")
        return node

    def errors(self, value: object, schema: object, path: str = "$") -> list:
        if schema is True:
            return []
        if schema is False:
            return [f"{path}: is not allowed"]
        if not isinstance(schema, dict):
            raise SchemaError(f"schema at {path} must be an object or boolean")
        unknown = set(schema) - KEYWORDS - ANNOTATIONS
        if unknown:
            raise SchemaError(f"unsupported schema keywords {sorted(unknown)}")
        found: list = []
        if "$ref" in schema:
            found += self.errors(value, self.resolve(schema["$ref"]), path)
        for sub in schema.get("allOf", []):
            found += self.errors(value, sub, path)
        if "anyOf" in schema and all(self.errors(value, sub, path) for sub in schema["anyOf"]):
            found.append(f"{path}: does not match any allowed form")
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(value, expected) for expected in types):
                return found + [f"{path}: expected {' or '.join(types)}"]
        if "const" in schema and value != schema["const"]:
            found.append(f"{path}: must equal {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            found.append(f"{path}: must be one of {schema['enum']}")
        if isinstance(value, str):
            if len(value.strip()) < schema.get("minLength", 0):
                found.append(f"{path}: must be a non-empty string")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                found.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                found.append(f"{path}: needs at least {schema['minItems']} item(s)")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                found.append(f"{path}: allows at most {schema['maxItems']} item(s)")
            if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
                found.append(f"{path}: items must be unique")
            if "items" in schema:
                for index, item in enumerate(value):
                    found += self.errors(item, schema["items"], f"{path}[{index}]")
        if isinstance(value, dict):
            if len(value) < schema.get("minProperties", 0):
                found.append(f"{path}: must not be empty")
            for name in schema.get("required", []):
                if name not in value:
                    found.append(f"{path}: missing required field {name}")
            properties = schema.get("properties", {})
            for name, item in value.items():
                if name in properties:
                    found += self.errors(item, properties[name], f"{path}.{name}")
                elif "additionalProperties" in schema:
                    found += self.errors(item, schema["additionalProperties"], f"{path}.{name}")
        return found


def stable_ids(document: dict) -> tuple:
    ids: list = []
    for collection in COLLECTIONS:
        for record in document.get(collection, []) if isinstance(document.get(collection), list) else []:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                ids.append(record["id"])
    return ids, set(ids)


def semantic_errors(document: dict, check_references: bool) -> list:
    errors: list = []
    ids, known = stable_ids(document)
    for identifier in sorted({item for item in ids if ids.count(item) > 1}):
        errors.append(f"duplicate stable id: {identifier}")
    if not check_references:
        return errors
    for collection in COLLECTIONS:
        for record in document.get(collection, []) if isinstance(document.get(collection), list) else []:
            if not isinstance(record, dict):
                continue
            for reference in record.get("related_ids", []) if isinstance(record.get("related_ids"), list) else []:
                if reference == record.get("id"):
                    errors.append(f"{record.get('id')} references itself")
                elif reference not in known:
                    errors.append(f"{record.get('id')} references missing id {reference}")
    for index, edge in enumerate(document.get("traceability", []) if isinstance(document.get("traceability"), list) else []):
        if isinstance(edge, dict):
            for endpoint in [edge.get("from")] + (edge.get("to") if isinstance(edge.get("to"), list) else []):
                if isinstance(endpoint, str) and endpoint not in known:
                    errors.append(f"traceability[{index}] references missing id {endpoint}")
    return errors


def audit(schema: object, validator: Validator, path: str = "#") -> None:
    """Statically reject unsupported keywords and broken $ref anywhere in the schema."""
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise SchemaError(f"{path} must be an object or boolean")
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise SchemaError(f"{path} uses unsupported keywords {sorted(unknown)}")
    if "$ref" in schema:
        validator.resolve(schema["$ref"])
    for name, sub in schema.get("properties", {}).items():
        audit(sub, validator, f"{path}/properties/{name}")
    for name, sub in schema.get("$defs", {}).items():
        audit(sub, validator, f"{path}/$defs/{name}")
    for keyword in ("items", "additionalProperties"):
        if keyword in schema:
            audit(schema[keyword], validator, f"{path}/{keyword}")
    for keyword in ("allOf", "anyOf"):
        for index, sub in enumerate(schema.get(keyword, [])):
            audit(sub, validator, f"{path}/{keyword}/{index}")


def load_schema(path: Path) -> Validator:
    schema = load(path)
    if not isinstance(schema, dict) or schema.get("$id") != SCHEMA_IDS[path]:
        raise SchemaError(f"{path.name} has unexpected $id")
    validator = Validator(schema)
    audit(schema, validator)
    return validator


def validate_document(document: object, state_validator: Validator, handoff_validator: Validator) -> list:
    if isinstance(document, dict) and "state_patch" in document:
        errors = handoff_validator.errors(document, handoff_validator.root)
        patch = document.get("state_patch")
        if isinstance(patch, dict):
            errors += [f"state_patch: {error}" for error in semantic_errors(patch, check_references=False)]
        return errors
    errors = state_validator.errors(document, state_validator.root)
    if isinstance(document, dict):
        errors += semantic_errors(document, check_references=True)
    return errors


def main() -> int:
    paths = [Path(arg) for arg in sys.argv[1:]] or [ROOT / "tests" / "system-design" / "fixtures" / "low-traffic.json"]
    try:
        state_validator, handoff_validator = load_schema(STATE_SCHEMA), load_schema(HANDOFF_SCHEMA)
    except (OSError, ValueError, SchemaError) as exc:
        print(f"CONTRACT SCHEMA ERROR: {exc}")
        return 2
    errors: list = []
    for path in paths:
        try:
            document = load(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        try:
            errors.extend(f"{path}: {error}" for error in validate_document(document, state_validator, handoff_validator))
        except SchemaError as exc:
            print(f"CONTRACT SCHEMA ERROR: {exc}")
            return 2
    if errors:
        print("CONTRACT VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"CONTRACT VALIDATION PASSED for {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
