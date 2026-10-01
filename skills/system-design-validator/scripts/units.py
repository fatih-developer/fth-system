#!/usr/bin/env python3
"""Dimensional analysis for EST-* records (estimate unit contract v1.0).

This module is duplicated byte-for-byte in every skill that evaluates
estimates so each skill stays installable on its own. The repository
regression suite fails when the copies drift.

An estimate is verifiable when it declares named, unit-bearing inputs, a
formula over those names, and a declared result value and unit:

    {"formula": "peak_rps * payload",
     "inputs": {"peak_rps": {"value": 100, "unit": "req/s"},
                "payload": {"value": 1, "unit": "KB/req"}},
     "value": 0.8, "unit": "Mbit/s"}

Bare numeric literals in a formula are dimensionless. Unit conversion is
implicit, so a literal such as ``/ 60`` or ``* 8`` is a scaling factor and
never a unit conversion.
"""

from __future__ import annotations

import ast
import math
import re
from typing import Dict, Tuple

Dims = Tuple[Tuple[str, int], ...]
RELATIVE_TOLERANCE = 0.01


class UnitError(ValueError):
    """Raised when a unit or formula cannot be verified."""


_TIME = {
    "ns": 1e-9, "us": 1e-6, "µs": 1e-6, "ms": 1e-3, "s": 1.0, "sec": 1.0, "second": 1.0,
    "min": 60.0, "minute": 60.0, "h": 3600.0, "hr": 3600.0, "hour": 3600.0,
    "d": 86400.0, "day": 86400.0, "week": 604800.0, "wk": 604800.0,
    "month": 2592000.0, "mo": 2592000.0, "year": 31536000.0, "yr": 31536000.0,
}
# Data units are case-sensitive: decimal SI (KB = 1000 B) and binary IEC (KiB = 1024 B).
_DATA = {
    "B": 1.0, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "PB": 1e15,
    "KiB": 1024.0, "MiB": 1024.0 ** 2, "GiB": 1024.0 ** 3, "TiB": 1024.0 ** 4, "PiB": 1024.0 ** 5,
    "bit": 0.125, "Kbit": 125.0, "kbit": 125.0, "Mbit": 1.25e5, "Gbit": 1.25e8, "Tbit": 1.25e11,
}
_DATA_WORDS = {"byte": 1.0, "bytes": 1.0, "bits": 0.125}
_AMBIGUOUS = {"b", "kb", "mb", "gb", "tb", "Kb", "Mb", "Gb", "Tb", "m", "M"}
_COUNTS = {
    "event", "request", "query", "message", "user", "record", "op", "operation", "order",
    "transfer", "transaction", "url", "item", "connection", "session", "device", "object",
    "write", "read", "click", "node", "server", "instance", "core", "page", "file", "key",
    "batch", "job", "task", "entry", "account", "row", "document", "partition", "shard",
    "notification", "payment", "redirect", "upload", "download", "packet",
}
_COUNT_ALIASES = {"req": "request", "msg": "message", "txn": "transaction", "conn": "connection", "doc": "document", "queries": "query", "entries": "entry"}
_DIMENSIONLESS = {"1": 1.0, "x": 1.0, "ratio": 1.0, "factor": 1.0, "replica": 1.0, "copy": 1.0, "copies": 1.0, "%": 0.01, "percent": 0.01}
_CURRENCY = {"USD", "EUR", "GBP", "TRY"}
_RATES = {
    "rps": "request/s", "qps": "query/s", "tps": "transaction/s",
    "bps": "bit/s", "Kbps": "Kbit/s", "kbps": "Kbit/s", "Mbps": "Mbit/s", "Gbps": "Gbit/s",
}
_TOKEN_RE = re.compile(r"^([^\^]+)(?:\^(-?\d+))?$")


def _normalize(dims: Dict[str, int]) -> Dims:
    return tuple(sorted((name, exp) for name, exp in dims.items() if exp))


def _atom(token: str) -> Tuple[float, Dict[str, int]]:
    if token in _RATES:
        return parse_unit_raw(_RATES[token])
    if token in _AMBIGUOUS:
        raise UnitError(f"ambiguous unit '{token}'; use B/KB/MB (bytes), bit/Kbit/Mbit (bits), min (minutes)")
    if token in _DATA:
        return _DATA[token], {"data": 1}
    if token in _CURRENCY:
        return 1.0, {f"currency:{token}": 1}
    lowered = token.lower()
    if lowered in _DATA_WORDS:
        return _DATA_WORDS[lowered], {"data": 1}
    if lowered in _DIMENSIONLESS:
        return _DIMENSIONLESS[lowered], {}
    candidates = [lowered]
    if lowered.endswith("ies"):
        candidates.append(lowered[:-3] + "y")
    if lowered.endswith("es"):
        candidates.append(lowered[:-2])
    if lowered.endswith("s"):
        candidates.append(lowered[:-1])
    for candidate in candidates:
        if candidate in _TIME:
            return _TIME[candidate], {"time": 1}
        if candidate in _DIMENSIONLESS:
            return _DIMENSIONLESS[candidate], {}
        canonical = _COUNT_ALIASES.get(candidate, candidate)
        if canonical in _COUNTS:
            return 1.0, {f"count:{canonical}": 1}
    raise UnitError(f"unknown unit '{token}'")


def _product(part: str) -> Tuple[float, Dict[str, int]]:
    factor, dims = 1.0, {}
    tokens = [token for token in re.split(r"[*·\s]+", part.strip()) if token]
    if not tokens:
        raise UnitError("empty unit component")
    for token in tokens:
        match = _TOKEN_RE.match(token)
        if not match:
            raise UnitError(f"malformed unit token '{token}'")
        name, exponent = match.group(1), int(match.group(2) or 1)
        atom_factor, atom_dims = _atom(name)
        factor *= atom_factor ** exponent
        for dim, exp in atom_dims.items():
            dims[dim] = dims.get(dim, 0) + exp * exponent
    return factor, dims


def parse_unit_raw(unit: str) -> Tuple[float, Dict[str, int]]:
    if not isinstance(unit, str) or not unit.strip():
        raise UnitError("unit must be a non-empty string")
    text = re.sub(r"\s+per\s+", "/", unit.strip())
    parts = text.split("/")
    factor, dims = _product(parts[0])
    for part in parts[1:]:
        part_factor, part_dims = _product(part)
        factor /= part_factor
        for dim, exp in part_dims.items():
            dims[dim] = dims.get(dim, 0) - exp
    return factor, dims


def parse_unit(unit: str) -> Tuple[float, Dims]:
    factor, dims = parse_unit_raw(unit)
    return factor, _normalize(dims)


def describe(dims: Dims) -> str:
    if not dims:
        return "dimensionless"
    numerator = [f"{name}^{exp}" if exp != 1 else name for name, exp in dims if exp > 0]
    denominator = [f"{name}^{-exp}" if exp != -1 else name for name, exp in dims if exp < 0]
    text = "*".join(numerator) or "1"
    return text + ("/" + "/".join(denominator) if denominator else "")


class Quantity:
    __slots__ = ("value", "dims")

    def __init__(self, value: float, dims: Dims) -> None:
        self.value, self.dims = float(value), dims

    def _combine(self, other: "Quantity", sign: int) -> Dims:
        merged = dict(self.dims)
        for name, exp in other.dims:
            merged[name] = merged.get(name, 0) + sign * exp
        return _normalize(merged)


def _same(left: Quantity, right: Quantity, operation: str) -> None:
    if left.dims != right.dims:
        raise UnitError(f"cannot {operation} {describe(left.dims)} and {describe(right.dims)}")


def _evaluate(node: ast.AST, env: Dict[str, Quantity], used: set) -> Quantity:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, env, used)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return Quantity(node.value, ())
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise UnitError(f"formula uses undeclared input '{node.id}'")
        used.add(node.id)
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = _evaluate(node.operand, env, used)
        return Quantity(-operand.value if isinstance(node.op, ast.USub) else operand.value, operand.dims)
    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left, env, used)
        if isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int) and not isinstance(node.right.value, bool)):
                raise UnitError("exponents must be integer literals")
            return Quantity(left.value ** node.right.value, _normalize({name: exp * node.right.value for name, exp in left.dims}))
        right = _evaluate(node.right, env, used)
        if isinstance(node.op, ast.Add):
            _same(left, right, "add")
            return Quantity(left.value + right.value, left.dims)
        if isinstance(node.op, ast.Sub):
            _same(left, right, "subtract")
            return Quantity(left.value - right.value, left.dims)
        if isinstance(node.op, ast.Mult):
            return Quantity(left.value * right.value, left._combine(right, 1))
        if isinstance(node.op, ast.Div):
            if right.value == 0:
                raise UnitError("division by zero")
            return Quantity(left.value / right.value, left._combine(right, -1))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        args = [_evaluate(arg, env, used) for arg in node.args]
        if node.func.id in {"min", "max"} and args:
            for arg in args[1:]:
                _same(args[0], arg, f"take {node.func.id} of")
            pick = min if node.func.id == "min" else max
            return Quantity(pick(arg.value for arg in args), args[0].dims)
        if node.func.id in {"ceil", "floor"} and len(args) == 1:
            if args[0].dims:
                raise UnitError(f"{node.func.id}() requires a dimensionless argument, got {describe(args[0].dims)}")
            return Quantity((math.ceil if node.func.id == "ceil" else math.floor)(args[0].value), ())
    raise UnitError(f"unsupported formula syntax: {ast.dump(node)[:60]}")


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_estimate(estimate: dict) -> list:
    """Return a list of problems; an empty list means the estimate is dimensionally verified."""
    problems: list = []
    formula, inputs, unit, value = estimate.get("formula"), estimate.get("inputs"), estimate.get("unit"), estimate.get("value")
    if not isinstance(formula, str) or not formula.strip():
        problems.append("formula must be a non-empty expression over named inputs")
    if not isinstance(inputs, dict) or not inputs:
        problems.append("inputs must be an object mapping names to {value, unit}")
        inputs = {}
    if not is_number(value):
        problems.append("value must be the declared numeric result")
    env: Dict[str, Quantity] = {}
    for name, item in inputs.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            problems.append(f"input name '{name}' is not an identifier")
            continue
        if not isinstance(item, dict) or not is_number(item.get("value")) or not isinstance(item.get("unit"), str):
            problems.append(f"input '{name}' must have numeric value and unit")
            continue
        try:
            factor, dims = parse_unit(item["unit"])
        except UnitError as exc:
            problems.append(f"input '{name}': {exc}")
            continue
        env[name] = Quantity(item["value"] * factor, dims)
    try:
        declared_factor, declared_dims = parse_unit(unit) if isinstance(unit, str) else (None, None)
        if declared_factor is None:
            problems.append("unit must be a non-empty string")
    except UnitError as exc:
        problems.append(f"declared unit: {exc}")
        declared_factor = None
    if problems:
        return problems
    try:
        tree = ast.parse(formula, mode="eval")
        used: set = set()
        result = _evaluate(tree, env, used)
    except SyntaxError:
        return [f"formula is not a valid expression: {formula}"]
    except UnitError as exc:
        return [str(exc)]
    unused = sorted(set(env) - used)
    if unused:
        problems.append(f"declared inputs not used by formula: {unused}")
    if result.dims != declared_dims:
        problems.append(f"formula yields {describe(result.dims)} but unit '{unit}' is {describe(declared_dims)}")
        return problems
    computed = result.value / declared_factor
    if not math.isclose(computed, value, rel_tol=RELATIVE_TOLERANCE, abs_tol=1e-12):
        problems.append(f"formula evaluates to {computed:.6g} {unit} but value is {value:g} {unit}; numeric literals are dimensionless and never convert units")
    return problems


def same_dimension(left_unit: str, right_unit: str) -> bool:
    return parse_unit(left_unit)[1] == parse_unit(right_unit)[1]


def to_base(value: float, unit: str) -> float:
    return value * parse_unit(unit)[0]
