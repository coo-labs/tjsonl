"""tjsonl — Claude Code transcript jsonl schema extractor + validator.

Public API:
    walk(jsonl_path)        -> Iterator[Event]
    extract(jsonl_path)     -> dict          (observed schema)
    validate(jsonl_path)    -> ValidationReport
    load_spec(path=None)    -> dict          (the JSONSchema spec)

CLI entry point: `tj` (see cli.py).
"""

__version__ = "0.1.0"

from .walk import Event, ParseError, walk
from .extract import extract
from .validate import ValidationReport, validate
from ._spec import SPEC_VERSION, load_spec

__all__ = [
    "Event",
    "ParseError",
    "walk",
    "extract",
    "validate",
    "ValidationReport",
    "load_spec",
    "SPEC_VERSION",
    "__version__",
]
