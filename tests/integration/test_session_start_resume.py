"""Acceptance-falsifier integration test (per vade-app/vade-agent-logs#381).

Asks: *does the SessionStart hook fire on every session resume, reinjecting
identity context?*

The query: for each session in the local transcript cache, count the distinct
`toolUseID` values across `attachment.hook_success` events with
`hookEvent == "SessionStart"`. If any session shows count > 1, SessionStart
fires on resume in that session.

This is the falsifier the v0.1 spec must answer using only the `tj` library
— no custom one-off extractor, no ad-hoc jq.

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


def _session_start_toolUseIDs_per_session(transcripts_dir: Path) -> dict[str, set[str]]:
    """Walk every .jsonl under `transcripts_dir` via the `tj` walker; return a
    dict mapping session_id → set of distinct toolUseIDs that triggered a
    `hook_success` attachment with `hookEvent == "SessionStart"`."""
    per_session: dict[str, set[str]] = defaultdict(set)
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
                per_session[session_id].add(tool_use_id)
    return per_session


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

    per_session = _session_start_toolUseIDs_per_session(transcripts_dir)
    if not per_session:
        pytest.skip(
            "no SessionStart hook_success events observed in any cached transcript "
            "— corpus does not exercise the falsifier"
        )

    resumed = {sid: ids for sid, ids in per_session.items() if len(ids) > 1}

    # The falsifier passes when at least one session resumed and triggered
    # SessionStart a second time. The spec calls this "resume re-fires".
    assert resumed, (
        "Acceptance-falsifier failed: across "
        f"{len(per_session)} sessions with at least one SessionStart hook, "
        "none showed >1 distinct toolUseID. SessionStart did NOT fire on resume "
        "in this corpus. Either the corpus has no resumed sessions, or the hook "
        "behavior changed."
    )

    # Stable summary for the falsifier report.
    print(
        f"\n[falsifier] sessions with SessionStart: {len(per_session)}; "
        f"sessions resumed (>1 distinct toolUseID): {len(resumed)}; "
        f"max distinct toolUseIDs in a session: {max(len(v) for v in per_session.values())}"
    )
