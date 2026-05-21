"""Walker primitive — one line, one Event or ParseError."""

from __future__ import annotations

from pathlib import Path

from coo_transcripts_analysis.tj import walk, Event, ParseError

FIXTURES = Path(__file__).parent / "fixtures"


def test_walk_clean_minimal_yields_three_events():
    items = list(walk(FIXTURES / "clean_minimal.jsonl"))
    assert len(items) == 3
    assert all(isinstance(e, Event) for e in items)
    assert items[0].data["type"] == "user"
    assert items[1].data["type"] == "assistant"
    assert items[2].data["type"] == "attachment"


def test_walk_continues_past_malformed_lines():
    items = list(walk(FIXTURES / "malformed_lines.jsonl"))
    parse_errors = [i for i in items if isinstance(i, ParseError)]
    events = [i for i in items if isinstance(i, Event)]
    assert len(parse_errors) == 1
    assert parse_errors[0].line_number == 2
    assert len(events) == 2
    assert events[0].data["type"] == "user"
    assert events[1].data["type"] == "queue-operation"


def test_walk_line_numbers_are_one_based():
    items = list(walk(FIXTURES / "clean_minimal.jsonl"))
    line_numbers = [i.line_number for i in items]
    assert line_numbers == [1, 2, 3]
