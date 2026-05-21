# coo-transcripts-analysis

Tooling and a community-authored, observation-grounded **schema spec** for the on-disk JSONL transcript format Claude Code writes to `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.

Two surfaces sit in this repo:

1. **`spec/`** — the v0.1 schema spec (markdown + JSONSchema). Source of truth: [`spec/transcript-schema-spec.md`](spec/transcript-schema-spec.md).
2. **`tj`** — a thin Python library + CLI that walks a transcript jsonl, extracts its observed schema, and validates it against the spec. Implementation issue: [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381).

There is also `bin/transcript-pull-local.py` — the operator's R2 → local-cache puller, vendored from `vade-runtime`. Unrelated to `tj`; it's how you populate the integration-test corpus.

## Why this exists

Anthropic documents the storage location of the transcript jsonl, but not the per-line schema, version, or stability guarantee. Community parsers ([`ccusage`](https://github.com/ryoppippi/ccusage), [`claude-code-log`](https://github.com/daaain/claude-code-log), [`simonw/claude-code-transcripts`](https://github.com/simonw/claude-code-transcripts), and others) have converged independently on the same de-facto envelope. This repo documents that envelope explicitly, and ships the discipline that catches silent drift early. Full rationale in [vade-coo-memory#864](https://github.com/vade-app/vade-coo-memory/pull/864).

## Install

```bash
# From a checkout:
pip install -e .

# Or via uv:
uv pip install -e .
```

After install, `tj` is on PATH. Without install, run as `PYTHONPATH=src python3 -m coo_transcripts_analysis.tj.cli ...`.

## CLI

### `tj extract <jsonl>`

Walks a jsonl and emits an observed-schema JSON to stdout. Useful for "what's in this file?" and for drift-diff against a reference baseline.

```bash
tj extract transcripts/3a7bc761-e231-4ff4-be28-a3ef8ff9b700.jsonl | jq .top_level_types
# [
#   "assistant",
#   "attachment",
#   "last-prompt",
#   "queue-operation",
#   "user"
# ]
```

The output shape (see `extract()` docstring for the full key list):

```
schema_version, file, line_count, parsed_count, unparseable_count,
top_level_types, per_type_fields, attachment_types, hook_event_names,
content_block_types, tool_use_names, tool_use_input_keys
```

### `tj validate <jsonl> [--spec <path>]`

Validates a jsonl against the bundled `spec/transcript-schema.json` (or a path you provide). Emits a JSON report to stdout. Exit 0 on clean; exit 1 if any of the per-deliverable lists is non-empty.

Reports the exact set [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381) specified:

```
unknown_event_types
missing_required_fields
unknown_optional_fields
unknown_attachment_types
unknown_tool_names
unparseable_json
```

```bash
tj validate ~/.claude/projects/-home-user/3a7bc761-e231-4ff4-be28-a3ef8ff9b700.jsonl
echo $?     # 0 = clean, 1 = drift surfaced
```

## Library

```python
from coo_transcripts_analysis.tj import walk, extract, validate

# Line-by-line walker; yields Event or ParseError per non-blank line.
for evt in walk("session.jsonl"):
    print(evt.line_number, evt.data["type"])

# Observed-schema extractor.
schema = extract("session.jsonl")

# Validator.
report = validate("session.jsonl")
if not report.clean:
    print(report.unknown_attachment_types)
```

The library is **zero-dependency** on the runtime path. `pytest` is the only extra (under `[project.optional-dependencies] test`).

## Spec

[`spec/transcript-schema-spec.md`](spec/transcript-schema-spec.md) is the source-of-truth, observation-grounded spec. [`spec/transcript-schema.json`](spec/transcript-schema.json) is the JSONSchema (Draft 2020-12) rendering of the same, suitable for downstream consumers who want full schema-validator integration.

The spec covers:

- Eleven top-level event types (`assistant`, `attachment`, `user`, `system`, `last-prompt`, `queue-operation`, `pr-link`, plus four from [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) named with minimal detail).
- Per-type field tables grounded in the v0 174-session R2 sample.
- Twenty-one `attachment.type` discriminator values; `attachment.hook_success` payload is fully specified (the named v0 falsifier blocker per [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381)).
- `tool_use.input` as an extension point keyed on `tool_use.name`, with a closed registry of built-in tool names plus the `mcp__<server>__<action>` MCP pattern.
- A versioning convention with explicit field-add / field-rename / new-type rules.

## Acceptance falsifier — *does SessionStart fire on every session resume?*

The integration test under [`tests/integration/test_session_start_resume.py`](tests/integration/test_session_start_resume.py) answers the empirical question per the issue's acceptance criterion. It walks every `*.jsonl` in `transcripts/` via the `tj` library — **no custom jq, no one-off extractor** — and counts distinct `toolUseID` values across `attachment.hook_success` events with `hookEvent == "SessionStart"`. A session with >1 distinct `toolUseID` resumed at least once and SessionStart fired again.

```bash
./bin/transcript-pull-local.py                # populate transcripts/ from R2
pytest tests/integration -v
```

Empirical result on the v0 sample (174 sessions): 74 sessions showed >1 distinct SessionStart `toolUseID`. The hook **does** fire on resume, reinjecting identity context.

The test is marked `@pytest.mark.integration` and skips cleanly when `transcripts/` is empty (CI without the R2 cache).

## Running the test suite

```bash
pip install -e ".[test]"
pytest                                           # unit + integration (skips integration if no cache)
pytest -m "not integration"                     # unit only
COO_TRANSCRIPTS_DIR=/some/other/cache pytest tests/integration -v
```

## Repository layout

```
spec/
  transcript-schema-spec.md   ← canonical markdown spec
  transcript-schema.json      ← JSONSchema rendering
src/coo_transcripts_analysis/
  tj/
    walk.py                   ← line-by-line iterator primitive
    extract.py                ← observed-schema extractor
    validate.py               ← spec validator
    cli.py                    ← `tj` CLI entry point
    _spec.py                  ← spec loader + derived constants
tests/
  fixtures/*.jsonl            ← synthetic test inputs
  test_walk.py
  test_extract.py
  test_validate.py
  test_cli.py
  integration/
    test_session_start_resume.py  ← acceptance falsifier
bin/
  transcript-pull-local.py    ← R2 → local-cache (operator tool, not part of `tj`)
transcripts/                  ← .gitignored cache (populated by the puller)
```

## Maintenance

The schema spec is observation-grounded, not normative — when the underlying format changes, the spec follows. The discipline:

1. Every Claude Code minor-version release: extract schemas from a sample of post-release transcripts and diff against the spec. (v0 covers `extract` and `validate`; the drift-`diff` command is v1 work.)
2. Drift → open a spec PR. The PR explains which rule fired (field-add at required → major; field-add at optional → minor; new top-level type → minor; etc., per `spec/transcript-schema-spec.md` §11).
3. Downstream consumers (the `transcript-analyzer` agent, the live-observability epic [vade-agent-logs#348](https://github.com/vade-app/vade-agent-logs/issues/348)) pin to a spec version and bump deliberately.

## Cross-references

- [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381) — implementation issue.
- [vade-coo-memory#864](https://github.com/vade-app/vade-coo-memory/pull/864) — merged spec proposal this implementation lifts from.
- [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) — community schema-stability ask.
- [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) — aligned clean-room community parser.

## License

MIT — see [LICENSE](LICENSE).
