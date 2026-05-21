"""CLI surface (`tj extract`, `tj validate`)."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from coo_transcripts_analysis.tj import cli

FIXTURES = Path(__file__).parent / "fixtures"


def _run(argv: list[str]) -> tuple[int, dict]:
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main(argv)
    text = out.getvalue()
    parsed = json.loads(text) if text.strip() else {}
    return rc, parsed


def test_cli_extract_emits_observed_schema():
    rc, payload = _run(["extract", str(FIXTURES / "clean_minimal.jsonl")])
    assert rc == 0
    assert payload["schema_version"] == "0.1.0"
    assert "assistant" in payload["top_level_types"]


def test_cli_validate_clean_exits_zero():
    rc, payload = _run(["validate", str(FIXTURES / "clean_minimal.jsonl")])
    assert rc == 0
    assert payload["clean"] is True


def test_cli_validate_dirty_exits_one():
    rc, payload = _run(["validate", str(FIXTURES / "unknown_attachment.jsonl")])
    assert rc == 1
    assert payload["clean"] is False
    assert "something_new_in_v2_2" in payload["unknown_attachment_types"]
