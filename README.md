# tjsonl

**A community-maintained schema spec for Claude Code's on-disk transcript format, plus a zero-dependency Python CLI (`tj`) that validates against it.**

Anthropic publishes *where* Claude Code writes session transcripts — `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` — but not what's in them, how the shape will evolve, or what's stable. Half a dozen community parsers have converged independently on the same envelope: [`ccusage`](https://github.com/ryoppippi/ccusage), [`claude-code-log`](https://github.com/daaain/claude-code-log), [`simonw/claude-code-transcripts`](https://github.com/simonw/claude-code-transcripts), and others. This repo writes that envelope down once and ships the tooling to keep it honest as Claude Code evolves.

The goal is to be the **de-facto schema reference the community shares**, so peer-parser maintainers don't each have to re-do the drift-tracking work. PRs against the spec are the primary contribution — see [CONTRIBUTING.md](CONTRIBUTING.md) for the on-ramps (new event type, new `attachment.type`, new built-in tool).

Two surfaces:

1. **`spec/`** — the markdown spec. Source of truth: [`spec/transcript-schema-spec.md`](spec/transcript-schema-spec.md). The JSONSchema rendering is bundled in the `tjsonl` package (installed path `tjsonl/_bundled/transcript-schema.json`; in this repo, [`src/tjsonl/_bundled/transcript-schema.json`](src/tjsonl/_bundled/transcript-schema.json)).
2. **`tj`** — a Python library + CLI that extracts the observed schema from a transcript jsonl and validates it against the spec. Zero runtime dependencies.

## You should care if…

- You're writing tooling that reads Claude Code transcripts (cost tracking, replay, observability, audit, parsing).
- You've discovered the on-disk format empirically and want to stop re-discovering it on every Claude Code release.
- You maintain a peer parser and want to offload schema-tracking to a shared baseline.
- You want a CI gate that flags "Claude Code's transcript format drifted under us" the moment it happens.

## Install

```bash
pip install tjsonl
# or, from a checkout:
pip install -e .
```

After install, `tj` is on PATH. Without install, run as `PYTHONPATH=src python3 -m tjsonl.cli ...`.

## Try it on your own transcripts

Claude Code writes a JSONL file per session at:

```
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
```

where `<encoded-cwd>` is the absolute path of the working directory you launched Claude Code in, with every non-alphanumeric character replaced by `-` (so `/home/alice/proj` becomes `-home-alice-proj`). Pick the most recent:

```bash
LATEST=$(ls -t ~/.claude/projects/*/*.jsonl | head -1)
tj extract "$LATEST" | jq .top_level_types
tj validate "$LATEST"
```

A clean run prints `"clean": true` and exits 0. A run with anything the spec doesn't know about exits 1 and lists what's new — that's the drift signal the spec is built around.

## CLI

### `tj extract <jsonl>`

Walks a jsonl and emits an observed-schema JSON to stdout. Useful for "what's in this file?" and (with `tj diff`, coming in v0.2) for drift-diff against a reference baseline.

```bash
tj extract ~/.claude/projects/-home-alice-proj/<id>.jsonl | jq .top_level_types
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

Exit codes: 0 always (unless the file isn't readable, in which case 2).

### `tj validate <jsonl> [--spec <path>]`

Validates a jsonl against the bundled spec (or a path you provide). Emits a JSON report to stdout.

Reports the exact set the spec's §10 names:

```
unknown_event_types
missing_required_fields
unknown_optional_fields
unknown_attachment_types
unknown_tool_names
unparseable_json
```

Exit codes:

- **0** — clean (every list above is empty, and `unparseable_json == 0`)
- **1** — drift surfaced (any of the above is non-zero/non-empty)
- **2** — invocation error (file not found, spec not loadable, etc.)

```bash
tj validate ~/.claude/projects/-home-alice-proj/<id>.jsonl
echo $?     # 0 = clean, 1 = drift, 2 = invocation error
```

## Library

```python
from tjsonl import walk, extract, validate

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

[`spec/transcript-schema-spec.md`](spec/transcript-schema-spec.md) is the source-of-truth, observation-grounded spec. The JSONSchema (Draft 2020-12) rendering of the same is bundled in the `tjsonl` package — suitable for downstream consumers who want full schema-validator integration. After install the path is `tjsonl/_bundled/transcript-schema.json` (in this repo, [`src/tjsonl/_bundled/transcript-schema.json`](src/tjsonl/_bundled/transcript-schema.json)). Fetch it raw at <https://raw.githubusercontent.com/vade-app/tjsonl/main/src/tjsonl/_bundled/transcript-schema.json>, or in Python via `tjsonl.load_spec()`.

The spec covers:

- Eleven top-level event types (`assistant`, `attachment`, `user`, `system`, `last-prompt`, `queue-operation`, `pr-link`, plus four from [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) named with minimal detail).
- Per-type field tables grounded in a 174-session sample.
- Twenty-one `attachment.type` discriminator values; `attachment.hook_success` payload is fully specified.
- `tool_use.input` as an extension point keyed on `tool_use.name`, with a closed registry of built-in tool names plus the `mcp__<server>__<action>` MCP pattern.
- A versioning convention with explicit field-add / field-rename / new-type rules, plus a deprecation policy (§11) downstream consumers can pin against.

## Contributing

We particularly want PRs from peer-parser maintainers when:

- Your parser observes an `attachment.type` value not in [spec §6](spec/transcript-schema-spec.md#6-attachmenttype-closed-enum-v01) — open an issue with a sample line, or open a PR adding the payload table directly.
- Your parser observes a top-level event type not in [spec §3](spec/transcript-schema-spec.md#3-top-level-types-closed-enum-v01) — same.
- A new built-in `tool_use.name` shows up (e.g. when Claude Code SDK adds one) — add it to `BUILTIN_TOOL_NAMES` in `src/tjsonl/_spec.py` and the §9 table.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the step-by-step on-ramps.

## Acceptance falsifier — *does SessionStart fire on every session resume?*

The integration test under [`tests/integration/test_session_start_resume.py`](tests/integration/test_session_start_resume.py) is held to an empirical question: for each `sessionId`, count distinct `toolUseID` values across `attachment.hook_success` events with `hookEvent == "SessionStart"`. A `sessionId` with >1 distinct `toolUseID` resumed at least once and SessionStart fired again.

```bash
COO_TRANSCRIPTS_DIR=~/.claude/projects pytest tests/integration -v
# or set COO_TRANSCRIPTS_DIR to any directory containing *.jsonl transcript files
```

Empirical result on a 174-file sample (195 distinct sessionIds): **5 of 195 sessionIds showed >1 distinct SessionStart `toolUseID`** — confirming the hook fires on resume. The test asserts on the per-`sessionId` measurement (matching the spec's per-session-lifetime semantics) and emits a per-file count as diagnostic output.

The test is marked `@pytest.mark.integration` and skips cleanly when no transcripts are visible (CI without a cache).

## Running the test suite

```bash
pip install -e ".[test]"
pytest                                         # unit + integration (skips integration if no cache)
pytest -m "not integration"                   # unit only
COO_TRANSCRIPTS_DIR=/path/to/cache pytest tests/integration -v
```

## Repository layout

```
spec/
  transcript-schema-spec.md   ← canonical markdown spec
  README.md                   ← pointer to the bundled JSONSchema
src/tjsonl/
  __init__.py                 ← public API: walk, extract, validate, load_spec
  walk.py                     ← line-by-line iterator primitive
  extract.py                  ← observed-schema extractor
  validate.py                 ← spec validator
  cli.py                      ← `tj` CLI entry point
  _spec.py                    ← spec loader + derived constants
  _bundled/                   ← JSONSchema bundled into the package
tests/
  fixtures/*.jsonl            ← synthetic test inputs
  test_walk.py / test_extract.py / test_validate.py / test_cli.py
  integration/test_session_start_resume.py  ← acceptance falsifier
```

## For VADE operators

The R2 ciphertext puller (`transcript-pull-local.py`) lives canonically at [`vade-app/vade-runtime/scripts/`](https://github.com/vade-app/vade-runtime) (private). Populate any directory with `*.jsonl` files using that, then point `tj` at it via `COO_TRANSCRIPTS_DIR=<path> pytest tests/integration` or just `tj validate <path.jsonl>`.

## Cross-references

- [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) — the community schema-stability ask.
- [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) — aligned clean-room community parser.
- [`ccusage`](https://github.com/ryoppippi/ccusage), [`claude-code-log`](https://github.com/daaain/claude-code-log), [`tokscale`](https://github.com/junhoyeo/tokscale), [`ClaudeCodeJSONLParser`](https://github.com/amac0/ClaudeCodeJSONLParser), [`claude-JSONL-browser`](https://github.com/withLinda/claude-JSONL-browser) — peer parsers.

## License

MIT — see [LICENSE](LICENSE).
