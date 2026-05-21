"""Spec loader — exposes the bundled spec/transcript-schema.json plus
derived constants the validator and extractor share.

The JSON spec is the single source of truth. This module surfaces it as
Python constants so the validator doesn't re-implement enums in code.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

SPEC_VERSION = "0.1.0"

# Built-in tool names known to Claude Code at v0.1 of this spec.
# MCP tools (mcp__<server>__<action>) are valid by pattern; their input
# shapes are the MCP server's responsibility, not this spec's.
BUILTIN_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "Agent",
        "AskUserQuestion",
        "Bash",
        "Edit",
        "ExitPlanMode",
        "Glob",
        "Grep",
        "Monitor",
        "MultiEdit",
        "NotebookEdit",
        "PushNotification",
        "Read",
        "SendUserFile",
        "Skill",
        "Task",
        "TodoWrite",
        "ToolSearch",
        "WebFetch",
        "WebSearch",
        "Write",
    }
)


@lru_cache(maxsize=8)
def load_spec(path: str | Path | None = None) -> dict:
    """Load the spec JSON.

    Defaults to the package-bundled `_bundled/transcript-schema.json` via
    `importlib.resources`, so it works under any install shape (editable,
    wheel, sdist, zipapp). Pass an explicit path to validate against an
    alternate spec.
    """
    if path:
        with Path(path).open("r", encoding="utf-8") as fh:
            return json.load(fh)
    with resources.files(__package__).joinpath("_bundled/transcript-schema.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def _per_type_definitions(spec: dict) -> dict[str, dict]:
    """Index the spec's top-level oneOf by event type."""
    out: dict[str, dict] = {}
    for variant in spec.get("oneOf", []):
        type_const = _extract_type_const(variant)
        if type_const:
            out[type_const] = variant
    return out


def _extract_type_const(variant: dict) -> str | None:
    """Pull the const value of `type` out of a top-level oneOf variant.

    Variants either:
      - declare {"type": {"const": "X"}} directly in `properties`, or
      - allOf a commonRich $ref + an object whose properties.type.const
        is the discriminator.
    """
    props = variant.get("properties")
    if props and isinstance(props, dict):
        tc = props.get("type", {})
        if isinstance(tc, dict) and "const" in tc:
            return tc["const"]
    for sub in variant.get("allOf", []) or []:
        sub_props = sub.get("properties") if isinstance(sub, dict) else None
        if sub_props and isinstance(sub_props, dict):
            tc = sub_props.get("type", {})
            if isinstance(tc, dict) and "const" in tc:
                return tc["const"]
    return None


@lru_cache(maxsize=8)
def known_event_types(spec_path: str | None = None) -> frozenset[str]:
    spec = load_spec(spec_path)
    return frozenset(_per_type_definitions(spec).keys())


@lru_cache(maxsize=8)
def known_attachment_types(spec_path: str | None = None) -> frozenset[str]:
    spec = load_spec(spec_path)
    per_type = _per_type_definitions(spec)
    attachment_variant = per_type.get("attachment")
    if not attachment_variant:
        return frozenset()
    for sub in attachment_variant.get("allOf", []) or []:
        props = sub.get("properties") if isinstance(sub, dict) else None
        if not props:
            continue
        attach = props.get("attachment", {})
        attach_props = attach.get("properties", {}) if isinstance(attach, dict) else {}
        type_field = attach_props.get("type", {})
        enum = type_field.get("enum") if isinstance(type_field, dict) else None
        if enum:
            return frozenset(enum)
    return frozenset()


def required_fields_for_type(event_type: str, spec_path: str | None = None) -> tuple[str, ...]:
    """Return the field names required at the envelope+per-type level for `event_type`.

    Returns a flat tuple of required field names (de-duplicated, order-preserving). For
    `assistant`, `attachment`, `user` this combines the commonRich requireds with the
    per-type requireds. For simpler types (`last-prompt`, `queue-operation`, etc.) this
    returns the variant's own `required` field.
    """
    spec = load_spec(spec_path)
    per_type = _per_type_definitions(spec)
    variant = per_type.get(event_type)
    if not variant:
        return ()
    fields: list[str] = []
    seen: set[str] = set()

    def _add(items):
        for f in items or []:
            if f not in seen:
                seen.add(f)
                fields.append(f)

    if "required" in variant:
        _add(variant["required"])
    for sub in variant.get("allOf", []) or []:
        if not isinstance(sub, dict):
            continue
        if "$ref" in sub:
            ref = sub["$ref"]
            # Resolve only the in-document $defs/commonRich case the spec uses.
            if ref == "#/$defs/commonRich":
                _add(spec.get("$defs", {}).get("commonRich", {}).get("required", []))
        if "required" in sub:
            _add(sub["required"])
    return tuple(fields)


def optional_fields_for_type(event_type: str, spec_path: str | None = None) -> frozenset[str]:
    """Return the union of envelope-level optional (non-required) field names enumerated
    in the spec for `event_type`. Used by the validator to detect *unknown* optional
    fields — fields that appear in the data but aren't enumerated in the spec at all.
    """
    spec = load_spec(spec_path)
    per_type = _per_type_definitions(spec)
    variant = per_type.get(event_type)
    if not variant:
        return frozenset()
    seen: set[str] = set()

    def _collect_properties(node):
        if not isinstance(node, dict):
            return
        props = node.get("properties")
        if isinstance(props, dict):
            seen.update(props.keys())
        for sub in node.get("allOf", []) or []:
            if isinstance(sub, dict):
                if "$ref" in sub and sub["$ref"] == "#/$defs/commonRich":
                    seen.update(
                        spec.get("$defs", {})
                        .get("commonRich", {})
                        .get("properties", {})
                        .keys()
                    )
                _collect_properties(sub)

    _collect_properties(variant)
    required = set(required_fields_for_type(event_type, spec_path))
    return frozenset(seen - required)
