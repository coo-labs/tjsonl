"""CLI surface (`tj extract`, `tj validate`)."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from tjsonl import cli

FIXTURES = Path(__file__).parent / "fixtures"


def _run(argv: list[str]) -> tuple[int, dict, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cli.main(argv)
    text = out.getvalue()
    parsed = json.loads(text) if text.strip() else {}
    return rc, parsed, err.getvalue()


def test_cli_extract_emits_observed_schema():
    rc, payload, _ = _run(["extract", str(FIXTURES / "clean_minimal.jsonl")])
    assert rc == 0
    assert payload["schema_version"] == "0.1.0"
    assert "assistant" in payload["top_level_types"]


def test_cli_validate_clean_exits_zero():
    rc, payload, _ = _run(["validate", str(FIXTURES / "clean_minimal.jsonl")])
    assert rc == 0
    assert payload["clean"] is True


def test_cli_validate_dirty_exits_one():
    rc, payload, _ = _run(["validate", str(FIXTURES / "unknown_attachment.jsonl")])
    assert rc == 1
    assert payload["clean"] is False
    assert "something_new_in_v2_2" in payload["unknown_attachment_types"]


def test_cli_extract_missing_file_exits_two_with_friendly_error():
    rc, payload, stderr = _run(["extract", "/tmp/tjsonl-no-such-file.jsonl"])
    assert rc == 2
    assert payload == {}
    assert "file not found" in stderr
    assert "Traceback" not in stderr


def test_cli_validate_missing_file_exits_two_with_friendly_error():
    rc, payload, stderr = _run(["validate", "/tmp/tjsonl-no-such-file.jsonl"])
    assert rc == 2
    assert payload == {}
    assert "file not found" in stderr


def test_cli_validate_missing_spec_file_exits_two():
    rc, _, stderr = _run(
        [
            "validate",
            str(FIXTURES / "clean_minimal.jsonl"),
            "--spec",
            "/tmp/tjsonl-no-such-spec.json",
        ]
    )
    assert rc == 2
    assert "spec file not found" in stderr


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "tjsonl" in (captured.out + captured.err)
