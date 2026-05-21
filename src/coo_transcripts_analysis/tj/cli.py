"""tj CLI — `tj extract <jsonl>` and `tj validate <jsonl>`.

Designed to be both a console_scripts entry (`tj`) and a `python -m
coo_transcripts_analysis.tj.cli` invocation, so callers without an
installed package (e.g., the transcript-analyzer agent running in
ad-hoc Bash) can still use it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .extract import extract
from .validate import validate


def _cmd_extract(args: argparse.Namespace) -> int:
    schema = extract(args.jsonl)
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).expanduser() if args.spec else None
    report = validate(args.jsonl, spec_path)
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
            "Claude Code transcript JSONL schema extractor + validator (v0). "
            "Spec: coo-transcripts-analysis/spec/transcript-schema-spec.md."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser(
        "extract",
        help="Emit observed schema of a transcript jsonl as JSON to stdout.",
    )
    pe.add_argument("jsonl", help="Path to the transcript .jsonl file.")
    pe.set_defaults(func=_cmd_extract)

    pv = sub.add_parser(
        "validate",
        help=(
            "Validate a transcript jsonl against the spec. "
            "Exit 0 on clean; exit 1 if any unknown event type, missing required "
            "field, unknown optional field, unknown attachment type, unknown tool "
            "name, or unparseable line is observed."
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
