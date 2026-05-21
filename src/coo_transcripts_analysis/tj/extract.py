"""Observed-schema extractor.

`extract(jsonl_path)` walks a jsonl and emits a dict describing the actual
shape of the events in that file. The output is intentionally close to the
Phase 2 drift extractor from the proposal — it's the same primitive,
promoted to a first-class library call.

The extractor is descriptive: it does not consult the spec. The validator
(see validate.py) is the side that reads the spec and decides what's
known vs unknown. Keeping the two separated means `extract` can run on
brand-new transcripts and surface new fields even before the spec has
caught up.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .walk import Event, ParseError, walk


def extract(jsonl_path: str | Path) -> dict:
    """Return an observed-schema dict for `jsonl_path`.

    Output keys:
      schema_version    — str, this extractor's output version
      file              — absolute path
      line_count        — total lines walked (excludes blank)
      parsed_count      — lines that parsed as JSON objects
      unparseable_count — lines that failed json.loads
      top_level_types   — sorted list of unique top-level `type` values
      per_type_fields   — per-event-type dict:
          required_in_all      — fields present on every observed event of that type
          optional_observed    — fields present on some but not all events of that type
          example_keys         — sorted union of all observed keys
          count                — number of events of this type
      attachment_types  — sorted list of unique `attachment.type` values
      hook_event_names  — sorted list of unique `attachment.hook_success.hookEvent` values
      content_block_types — per-role dict of message.content[].type discriminators
      tool_use_names    — sorted list of unique tool_use names
      tool_use_input_keys — per-tool dict: sorted list of input-key sets observed
    """
    path = Path(jsonl_path).resolve()
    per_type_key_sets: dict[str, list[set[str]]] = defaultdict(list)
    top_level_types: set[str] = set()
    attachment_types: set[str] = set()
    hook_event_names: set[str] = set()
    content_blocks_by_role: dict[str, set[str]] = defaultdict(set)
    tool_use_names: set[str] = set()
    tool_use_input_keys: dict[str, set[frozenset[str]]] = defaultdict(set)
    line_count = 0
    parsed_count = 0
    unparseable_count = 0

    for event in walk(path):
        line_count += 1
        if isinstance(event, ParseError):
            unparseable_count += 1
            continue
        parsed_count += 1
        data = event.data
        ev_type = data.get("type")
        if not isinstance(ev_type, str):
            continue
        top_level_types.add(ev_type)
        per_type_key_sets[ev_type].append(set(data.keys()))

        if ev_type == "attachment":
            att = data.get("attachment", {})
            if isinstance(att, dict):
                at_type = att.get("type")
                if isinstance(at_type, str):
                    attachment_types.add(at_type)
                if at_type == "hook_success":
                    hev = att.get("hookEvent")
                    if isinstance(hev, str):
                        hook_event_names.add(hev)

        if ev_type in ("assistant", "user"):
            msg = data.get("message", {})
            role = msg.get("role") if isinstance(msg, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list) and isinstance(role, str):
                for block in content:
                    if isinstance(block, dict):
                        bt = block.get("type")
                        if isinstance(bt, str):
                            content_blocks_by_role[role].add(bt)
                        if bt == "tool_use":
                            name = block.get("name")
                            if isinstance(name, str):
                                tool_use_names.add(name)
                                inp = block.get("input", {})
                                if isinstance(inp, dict):
                                    tool_use_input_keys[name].add(
                                        frozenset(inp.keys())
                                    )

    per_type_fields: dict[str, dict] = {}
    for ev_type, key_sets in per_type_key_sets.items():
        if not key_sets:
            continue
        union = set().union(*key_sets)
        intersection = set(key_sets[0])
        for ks in key_sets[1:]:
            intersection &= ks
        per_type_fields[ev_type] = {
            "required_in_all": sorted(intersection),
            "optional_observed": sorted(union - intersection),
            "example_keys": sorted(union),
            "count": len(key_sets),
        }

    return {
        "schema_version": "0.1.0",
        "file": str(path),
        "line_count": line_count,
        "parsed_count": parsed_count,
        "unparseable_count": unparseable_count,
        "top_level_types": sorted(top_level_types),
        "per_type_fields": per_type_fields,
        "attachment_types": sorted(attachment_types),
        "hook_event_names": sorted(hook_event_names),
        "content_block_types": {
            role: sorted(blocks) for role, blocks in sorted(content_blocks_by_role.items())
        },
        "tool_use_names": sorted(tool_use_names),
        "tool_use_input_keys": {
            name: sorted([sorted(ks) for ks in keysets])
            for name, keysets in sorted(tool_use_input_keys.items())
        },
    }
