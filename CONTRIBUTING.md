# Contributing to tjsonl

`tjsonl` is a community-maintained schema reference for Claude Code's on-disk JSONL transcript format. The spec is **descriptive, not prescriptive** — it tracks observed reality and bumps when reality changes. The most valuable contributions are:

1. Reporting drift between the spec and an actual transcript.
2. PR-ing field tables for opaque payloads when you've seen a real one.
3. Aligning the built-in tool registry when Claude Code ships a new tool.
4. Filling in the four event types currently named with minimal field detail (`agent-name`, `custom-title`, `file-history-snapshot`, `permission-mode`).

If your parser disagrees with this spec on any field, that's a bug in *one* of us — please open an issue with the evidence (one or two redacted jsonl lines) and we'll sort it.

---

## Three on-ramps

### A. Adding a new `attachment.type` payload

Eight of the 21 `attachment.type` values in [spec §6](spec/transcript-schema-spec.md#6-attachmenttype-closed-enum-v01) are still opaque (`Opaque object. To be filled in v1.`). If you've seen a real instance of one — `command_permissions`, `deferred_tools_delta`, `dynamic_skill`, `edited_text_file`, `nested_memory`, `queued_command`, `skill_listing`, `todo_reminder` — please PR a payload table.

The format is the same as `hook_success` (§6.1):

1. Add a sub-section under §6 named `### 6.N attachment.<type> payload`.
2. List the observed fields in a table with columns `Field | Type | Notes`.
3. Cite the empirical basis: "observed in N/N sessions in the v0 sample" or "observed in `<your-corpus-link>`".
4. Update [`src/tjsonl/_bundled/transcript-schema.json`](src/tjsonl/_bundled/transcript-schema.json) — add an `if/then` overlay on the `attachment` variant matching the `hook_success` pattern, OR push the payload structure inline.
5. Bump the spec version per §11 (new payload table → minor bump).

### B. Adding a new built-in `tool_use.name`

When Claude Code ships a new built-in tool, it shows up in `tool_use.name` and `tj validate` flags it as `unknown_tool_names`. To align:

1. Add the new name to `BUILTIN_TOOL_NAMES` in [`src/tjsonl/_spec.py`](src/tjsonl/_spec.py).
2. Add a row to the table in [spec §9](spec/transcript-schema-spec.md#9-tool_useinput-per-name-sub-schemas) with a link to the Claude Code SDK's type definition for that tool's input.
3. Bump the spec version per §11 (new built-in tool → minor bump).
4. Optional but appreciated: add a test fixture under `tests/fixtures/` exercising the new tool, and an assertion in `tests/test_validate.py`.

MCP tools (`mcp__<server>__<action>`) are valid by pattern; their input shapes are the MCP server's responsibility. Don't add MCP tool names to the built-in registry.

### C. Adding a new top-level event type

If your parser sees a `type` value not in [spec §3](spec/transcript-schema-spec.md#3-top-level-types-closed-enum-v01):

1. Add it as a `oneOf` variant in [`src/tjsonl/_bundled/transcript-schema.json`](src/tjsonl/_bundled/transcript-schema.json), with at minimum `type` + `sessionId` required and any per-type fields you can document.
2. Add a row to the §3 table with an empirical-evidence citation.
3. Add a `### 5.N <type>` sub-section in §5 with the per-type field table.
4. Bump the spec version per §11 (new top-level type → minor bump).
5. Update `BUILTIN_TOOL_NAMES` (no — that's tools, not events). Just the spec edit suffices; the validator picks up the new type via `known_event_types()`.

The four types currently sourced only from [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) (`agent-name`, `custom-title`, `file-history-snapshot`, `permission-mode`) are documented at envelope level only. PRs filling in their per-field detail from a real observation are exactly what the spec needs — see issue templates.

---

## Development workflow

```bash
git clone https://github.com/vade-app/tjsonl
cd tjsonl
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest                    # 18 tests + 1 integration (the integration skips if no transcripts)
```

To run the integration test against your own transcript cache:

```bash
COO_TRANSCRIPTS_DIR=~/.claude/projects pytest tests/integration -v
```

---

## PR checklist

- [ ] Spec markdown updated (if user-visible behavior changed).
- [ ] JSONSchema (`src/tjsonl/_bundled/transcript-schema.json`) updated to mirror the markdown.
- [ ] `_spec.py` constants reflect the change (if applicable — most spec changes are picked up automatically via JSON-driven constants).
- [ ] Tests added or updated.
- [ ] Spec version bumped per §11 (the PR can name which rule triggered).

---

## Reporting drift without coding

Not every contributor wants to write a PR. If you see drift but can't open the PR yourself:

1. Run `tj validate <your-jsonl>` and capture the output.
2. Open an issue titled `drift: <one-line description>`.
3. Paste the validator output. Include the Claude Code version (`grep '"version"' <jsonl>` — the field is on every common-rich line).
4. Include one or two example lines exhibiting the drift (redact any sensitive content).

The maintainers will turn it into a spec PR.

---

## Code of conduct

Be kind. Cite sources. When peer-parser maintainers contribute, treat their PRs with first-class priority — they're the load-bearing collaborators for the spec's purpose.

## License

MIT — see [LICENSE](../LICENSE). By contributing, you agree to license your contribution under the same.
