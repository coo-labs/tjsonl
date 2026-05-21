"""Observed-schema extractor."""

from __future__ import annotations

from pathlib import Path

from coo_transcripts_analysis.tj import extract

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_top_level_types():
    schema = extract(FIXTURES / "clean_minimal.jsonl")
    assert schema["top_level_types"] == ["assistant", "attachment", "user"]
    assert schema["parsed_count"] == 3
    assert schema["unparseable_count"] == 0


def test_extract_attachment_types_and_hook_events():
    schema = extract(FIXTURES / "clean_minimal.jsonl")
    assert schema["attachment_types"] == ["hook_success"]
    assert schema["hook_event_names"] == ["SessionStart"]


def test_extract_content_block_types_split_by_role():
    schema = extract(FIXTURES / "clean_minimal.jsonl")
    assert "user" in schema["content_block_types"]
    assert "assistant" in schema["content_block_types"]
    assert schema["content_block_types"]["user"] == ["text"]
    assert schema["content_block_types"]["assistant"] == ["text"]


def test_extract_required_in_all_intersection():
    schema = extract(FIXTURES / "resume_with_two_session_start.jsonl")
    # Every attachment line carries the common envelope.
    attach = schema["per_type_fields"]["attachment"]
    for required in (
        "type",
        "sessionId",
        "uuid",
        "parentUuid",
        "timestamp",
        "cwd",
        "entrypoint",
        "gitBranch",
        "isSidechain",
        "userType",
        "version",
        "attachment",
    ):
        assert required in attach["required_in_all"], required


def test_extract_handles_unparseable_lines_gracefully():
    schema = extract(FIXTURES / "malformed_lines.jsonl")
    assert schema["unparseable_count"] == 1
    assert schema["parsed_count"] == 2
    assert "user" in schema["top_level_types"]
    assert "queue-operation" in schema["top_level_types"]
