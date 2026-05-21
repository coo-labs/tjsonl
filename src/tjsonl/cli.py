"""tj CLI — `tj extract <jsonl>` and `tj validate <jsonl>`.

Designed to be both a console_scripts entry (`tj`) and a `python -m tjsonl.cli`
invocation, so callers without an installed package can still use it.

Exit codes:
  0  success / clean
  1  drift surfaced by validate
  2  invocation error (file not found, spec not loadable, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .extract import extract
from .validate import validate


def _err(msg: str) -> None:
    sys.stderr.write(f"tj: error: {msg}\n")


def _cmd_extract(args: argparse.Namespace) -> int:
    path = Path(args.jsonl)
    if not path.is_file():
        _err(f"file not found: {args.jsonl}")
        return 2
    try:
        schema = extract(path)
    except OSError as exc:
        _err(f"could not read {args.jsonl}: {exc}")
        return 2
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.jsonl)
    if not path.is_file():
        _err(f"file not found: {args.jsonl}")
        return 2
    spec_path = Path(args.spec).expanduser() if args.spec else None
    if spec_path is not None and not spec_path.is_file():
        _err(f"spec file not found: {args.spec}")
        return 2
    try:
        report = validate(path, spec_path)
    except OSError as exc:
        _err(f"could not read input: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        _err(f"spec file is not valid JSON: {exc}")
        return 2
    json.dump(_serialize_report(report), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return report.exit_code


def _serialize_report(report) -> dict:
    out = report.to_dict()
    for key in ("missing_required_fields", "unknown_optional_fields"):
        out[key] = [
            asdict(item) if not isinstance(item, dict) else item for item in out[key]
        ]
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tj",
        description=(
            "Claude Code transcript JSONL schema extractor + validator. "
            "Spec: spec/transcript-schema-spec.md."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"tj (tjsonl) {__version__}",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser(
        "extract",
        help="Emit observed schema of a transcript jsonl as JSON to stdout.",
        description=(
            "Walks the jsonl and prints an observed-schema JSON describing "
            "every top-level type, attachment.type, content-block type, tool "
            "name, and tool-input key-set actually present in the file. "
            "Exit 0 on success; 2 on invocation error."
        ),
    )
    pe.add_argument("jsonl", help="Path to the transcript .jsonl file.")
    pe.set_defaults(func=_cmd_extract)

    pv = sub.add_parser(
        "validate",
        help=(
            "Validate a transcript jsonl against the spec. Exit 0 on clean; "
            "1 on drift; 2 on invocation error."
        ),
        description=(
            "Validates each non-blank line against the v0.1 spec. Reports "
            "unknown_event_types, missing_required_fields, "
            "unknown_optional_fields, unknown_attachment_types, "
            "unknown_tool_names, and unparseable_json. "
            "Exit 0 when every bucket is empty and unparseable_json == 0. "
            "Exit 1 on any drift; 2 on invocation error."
        ),
    )
    pv.add_argument("jsonl", help="Path to the transcript .jsonl file.")
    pv.add_argument(
        "--spec",
        default=None,
        help="Path to an alternate transcript-schema.json (default: bundled spec).",
    )
    pv.set_defaults(func=_cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
