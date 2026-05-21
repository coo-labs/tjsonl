"""Spec validator."""

from __future__ import annotations

from pathlib import Path

from coo_transcripts_analysis.tj import validate

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_clean_minimal_is_clean():
    report = validate(FIXTURES / "clean_minimal.jsonl")
    assert report.clean is True
    assert report.exit_code == 0
    assert report.unknown_event_types == []
    assert report.missing_required_fields == []
    assert report.unknown_optional_fields == []
    assert report.unknown_attachment_types == []
    assert report.unknown_tool_names == []
    assert report.unparseable_json == 0


def test_validate_resume_fixture_is_clean():
    """Two distinct SessionStart hook_success toolUseIDs on one sessionId — the falsifier
    pattern. The validator must accept this as well-formed against v0.1."""
    report = validate(FIXTURES / "resume_with_two_session_start.jsonl")
    assert report.clean is True


def test_validate_unknown_attachment_type_is_reported():
    report = validate(FIXTURES / "unknown_attachment.jsonl")
    assert report.clean is False
    assert report.exit_code == 1
    assert "something_new_in_v2_2" in report.unknown_attachment_types


def test_validate_malformed_lines_counted_as_unparseable():
    report = validate(FIXTURES / "malformed_lines.jsonl")
    assert report.unparseable_json == 1
    # one parsed line is a user without `message` content list — but the synthetic
    # fixture passes a string content, which the spec allows on user via oneOf.
    assert report.exit_code == 1  # unparseable counts as not-clean
