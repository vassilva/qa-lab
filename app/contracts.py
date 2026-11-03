"""
Validation of messages against the JSON Schema contracts in contracts/.

Implements the subset of JSON Schema used by the project's contracts (type, required, properties,
additionalProperties, pattern, const, enum, minimum, exclusiveMinimum), with no external dependencies.
The contract files are standard JSON Schema: any tool can check them.
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS_DIR = os.path.join(BASE_DIR, "contracts")
_TYPES = {"object": dict, "string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list}


def load(name):
    with open(os.path.join(CONTRACTS_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def errors(value, schema, path="$"):
    """List of errors (empty = valid)."""
    out = []
    if "const" in schema and value != schema["const"]:
        return [f"{path}: expected {schema['const']!r}, got {value!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: {value!r} is not one of {schema['enum']}"]
    t = schema.get("type")
    if t:
        ok = isinstance(value, _TYPES[t]) and not (t in ("integer", "number") and isinstance(value, bool))
        if not ok:
            return [f"{path}: expected type {t}, got {type(value).__name__}"]
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        out.append(f"{path}: {value!r} does not match pattern {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            out.append(f"{path}: {value} must be > {schema['exclusiveMinimum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                out.append(f"{path}: missing required field: {req}")
        if schema.get("additionalProperties") is False:
            for extra in sorted(set(value) - set(props)):
                out.append(f"{path}: field not in contract: {extra}")
        for k, sub in props.items():
            if k in value:
                out += errors(value[k], sub, f"{path}.{k}")
    return out


TRADE_EXECUTED = load("trade-executed.v1.schema.json")


def validate_trade_executed(event):
    return errors(event, TRADE_EXECUTED)
