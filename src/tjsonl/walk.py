"""Line-by-line walker over a Claude Code transcript jsonl.

The walker is the single parse primitive every other tj module sits on. It
treats each line as an independent parse unit (per the spec's "treat each
line as an independent parse unit, not slurp the whole file" guidance) so
one malformed line doesn't poison the iterator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class ParseError:
    """One line that failed json.loads."""

    line_number: int
    raw: str
    error: str


@dataclass(frozen=True)
class Event:
    """One successfully-parsed jsonl line.

    `line_number` is 1-based. `data` is the parsed JSON object.
    """

    line_number: int
    data: dict


def walk(jsonl_path: str | Path) -> Iterator[Event | ParseError]:
    """Yield one Event or ParseError per non-blank line in `jsonl_path`.

    Blank lines are skipped silently. Each line is parsed in isolation; a
    JSONDecodeError on one line does not stop iteration.
    """
    path = Path(jsonl_path)
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                yield ParseError(
                    line_number=line_no,
                    raw=stripped[:200],
                    error=str(exc),
                )
                continue
            if not isinstance(data, dict):
                yield ParseError(
                    line_number=line_no,
                    raw=stripped[:200],
                    error=f"line is not a JSON object (got {type(data).__name__})",
                )
                continue
            yield Event(line_number=line_no, data=data)
