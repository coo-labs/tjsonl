"""Acceptance-falsifier integration test (per vade-app/vade-agent-logs#381).

Asks: *does the SessionStart hook fire on every session resume, reinjecting
identity context?*

The query: for each `sessionId` observed across the local transcript cache,
count the distinct `toolUseID` values across `attachment.hook_success` events
with `hookEvent == "SessionStart"`. If any `sessionId` shows count > 1,
SessionStart fired a second time on that session — a resume event.

Two units of measurement coexist:

  - **per `sessionId`** (the canonical unit; the on-disk filename is
    `<sessionId>.jsonl` but a single file pulled from R2 can contain lines
    carrying *other* sessionIds — sub-agent sidechains, export merges, the
    spec's `isSidechain` flag). The spec's §6.1 resume-firing semantics
    are defined per session lifetime, i.e. per sessionId.
  - **per file** (the on-disk grouping). Useful for fleet ops where each
    `.jsonl` is a deployment unit, but it conflates multiple in-line
    sessionIds.

The assertion is **per sessionId** because that's what the spec means by
"session." The diagnostic output reports both numbers so a reader can
reconcile them.

Skipped if `transcripts/` is empty (CI without the local R2 cache).
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import pytest

from coo_transcripts_analysis.tj import walk, Event

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO_ROOT / "transcripts"


def _transcript_dir() -> Path:
    override = os.environ.get("COO_TRANSCRIPTS_DIR")
    return Path(override).expanduser().resolve() if override else DEFAULT_DIR


def _session_start_counts(transcripts_dir: Path) -> tuple[dict[str, set[str]], dict[Path, set[str]]]:
    """Walk every .jsonl under `transcripts_dir` via the `tj` walker.

    Returns:
      per_session_id  — sessionId (from the line) → set of distinct toolUseIDs
                        observed on `hook_success` attachments with
                        `hookEvent == "SessionStart"`.
      per_file        — file path → same set, grouped by on-disk file.
    """
    per_session_id: dict[str, set[str]] = defaultdict(set)
    per_file: dict[Path, set[str]] = defaultdict(set)
    for path in sorted(transcripts_dir.glob("*.jsonl")):
        for evt in walk(path):
            if not isinstance(evt, Event):
                continue
            d = evt.data
            if d.get("type") != "attachment":
                continue
            att = d.get("attachment") or {}
            if att.get("type") != "hook_success":
                continue
            if att.get("hookEvent") != "SessionStart":
                continue
            session_id = d.get("sessionId")
            tool_use_id = att.get("toolUseID")
            if isinstance(session_id, str) and isinstance(tool_use_id, str):
                per_session_id[session_id].add(tool_use_id)
                per_file[path].add(tool_use_id)
    return per_session_id, per_file


@pytest.mark.integration
def test_session_start_fires_on_resume():
    transcripts_dir = _transcript_dir()
    if not transcripts_dir.is_dir():
        pytest.skip(
            f"no transcript cache at {transcripts_dir}; set COO_TRANSCRIPTS_DIR or "
            "run bin/transcript-pull-local.py to populate"
        )

    sessions = sorted(transcripts_dir.glob("*.jsonl"))
    if not sessions:
        pytest.skip(f"transcript cache at {transcripts_dir} is empty")

    per_session_id, per_file = _session_start_counts(transcripts_dir)
    if not per_session_id:
        pytest.skip(
            "no SessionStart hook_success events observed in any cached transcript "
            "— corpus does not exercise the falsifier"
        )

    resumed_session_ids = {sid: ids for sid, ids in per_session_id.items() if len(ids) > 1}
    resumed_files = {p: ids for p, ids in per_file.items() if len(ids) > 1}

    # Stable summary printed unconditionally so a reader can reconcile the two
    # units of measurement.
    print(
        f"\n[falsifier] sessionIds with SessionStart: {len(per_session_id)}; "
        f"sessionIds resumed (>1 distinct toolUseID): {len(resumed_session_ids)}; "
        f"max distinct toolUseIDs in a sessionId: "
        f"{max(len(v) for v in per_session_id.values())}"
    )
    print(
        f"[falsifier] files with SessionStart: {len(per_file)}; "
        f"files with >1 distinct toolUseID: {len(resumed_files)}; "
        f"max distinct toolUseIDs in a file: "
        f"{max(len(v) for v in per_file.values())}"
    )

    # The falsifier passes when at least one session resumed and triggered
    # SessionStart a second time. The spec calls this "resume re-fires."
    # Measurement unit is per sessionId per spec §6.1.
    assert resumed_session_ids, (
        "Acceptance-falsifier failed: across "
        f"{len(per_session_id)} sessionIds with at least one SessionStart hook, "
        "none showed >1 distinct toolUseID. SessionStart did NOT fire on resume "
        "in this corpus. Either the corpus has no resumed sessions, or the hook "
        "behavior changed."
    )
