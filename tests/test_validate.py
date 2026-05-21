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


def test_validate_missing_or_non_string_type_is_reported():
    """`type` is required on every line per spec §2; a missing or non-string
    value must surface as a missing-required-field row, not silently pass."""
    report = validate(FIXTURES / "missing_type.jsonl")
    assert report.clean is False
    assert report.exit_code == 1
    type_misses = [
        m for m in report.missing_required_fields if m.field == "type"
    ]
    assert len(type_misses) == 2
    assert {m.line_number for m in type_misses} == {1, 2}
    assert all(m.event_type == "<unknown>" for m in type_misses)


def test_validate_reports_missing_required_envelope_fields():
    """An assistant line that omits common-rich envelope fields surfaces them
    as missing-required-field rows (line numbers included)."""
    report = validate(FIXTURES / "missing_required.jsonl")
    assert report.clean is False
    missing_names = {m.field for m in report.missing_required_fields}
    assert "parentUuid" in missing_names
