"""Spec validator.

`validate(jsonl_path)` walks a jsonl and checks each line against the
v0.1 spec. Returns a ValidationReport whose keys are exactly the set
[vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381)'s
deliverables list specifies:

    unknown_event_types
    missing_required_fields
    unknown_optional_fields
    unknown_attachment_types
    unknown_tool_names
    unparseable_json

The validator is intentionally structural — not a full JSONSchema engine —
so the package stays zero-dependency. Coverage matches the spec's
described constraints (top-level enum, common-rich requireds, attachment
enum, tool-name registry, MCP-name pattern). The bundled JSONSchema in
spec/transcript-schema.json is the machine-readable reference for
downstream consumers that want full Draft 2020-12 validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import _spec
from .walk import Event, ParseError, walk

_MCP_TOOL_NAME = re.compile(r"^mcp__[A-Za-z0-9_\-]+__[A-Za-z0-9_\-]+$")


@dataclass
class MissingField:
    line_number: int
    event_type: str
    field: str


@dataclass
class UnknownOptional:
    line_number: int
    event_type: str
    field: str


@dataclass
class ValidationReport:
    """Per-#381 validator output shape.

    Each list captures every observation. The summary `clean` and `exit_code`
    properties fold the lists into the issue's "exit 0 on clean; exit 1 on any
    unknown" rule.
    """

    file: str
    spec_version: str
    line_count: int = 0
    parsed_count: int = 0
    unparseable_json: int = 0
    unknown_event_types: list[str] = field(default_factory=list)
    missing_required_fields: list[MissingField] = field(default_factory=list)
    unknown_optional_fields: list[UnknownOptional] = field(default_factory=list)
    unknown_attachment_types: list[str] = field(default_factory=list)
    unknown_tool_names: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return (
            self.unparseable_json == 0
            and not self.unknown_event_types
            and not self.missing_required_fields
            and not self.unknown_optional_fields
            and not self.unknown_attachment_types
            and not self.unknown_tool_names
        )

    @property
    def exit_code(self) -> int:
        return 0 if self.clean else 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["clean"] = self.clean
        return d


def validate(jsonl_path: str | Path, spec_path: str | Path | None = None) -> ValidationReport:
    """Walk a jsonl and validate each line against the v0.1 spec."""
    path = Path(jsonl_path).resolve()
    spec_arg = str(spec_path) if spec_path else None
    known_types = _spec.known_event_types(spec_arg)
    known_attachments = _spec.known_attachment_types(spec_arg)

    report = ValidationReport(file=str(path), spec_version=_spec.SPEC_VERSION)
    seen_unknown_event_types: set[str] = set()
    seen_unknown_attachments: set[str] = set()
    seen_unknown_tools: set[str] = set()

    for event in walk(path):
        report.line_count += 1
        if isinstance(event, ParseError):
            report.unparseable_json += 1
            continue
        report.parsed_count += 1
        data = event.data
        ev_type = data.get("type")
        if not isinstance(ev_type, str):
            continue

        if ev_type not in known_types:
            if ev_type not in seen_unknown_event_types:
                seen_unknown_event_types.add(ev_type)
                report.unknown_event_types.append(ev_type)
            continue

        required = _spec.required_fields_for_type(ev_type, spec_arg)
        known_optional = _spec.optional_fields_for_type(ev_type, spec_arg)
        for f_name in required:
            if f_name not in data:
                report.missing_required_fields.append(
                    MissingField(
                        line_number=event.line_number, event_type=ev_type, field=f_name
                    )
                )
        envelope_known = set(required) | set(known_optional)
        for k in data.keys():
            if k not in envelope_known:
                report.unknown_optional_fields.append(
                    UnknownOptional(
                        line_number=event.line_number, event_type=ev_type, field=k
                    )
                )

        if ev_type == "attachment":
            att = data.get("attachment", {})
            if isinstance(att, dict):
                at_type = att.get("type")
                if isinstance(at_type, str) and at_type not in known_attachments:
                    if at_type not in seen_unknown_attachments:
                        seen_unknown_attachments.add(at_type)
                        report.unknown_attachment_types.append(at_type)

        if ev_type in ("assistant", "user"):
            msg = data.get("message", {})
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    if isinstance(name, str) and not _is_known_tool_name(name):
                        if name not in seen_unknown_tools:
                            seen_unknown_tools.add(name)
                            report.unknown_tool_names.append(name)

    return report


def _is_known_tool_name(name: str) -> bool:
    return name in _spec.BUILTIN_TOOL_NAMES or bool(_MCP_TOOL_NAME.match(name))
