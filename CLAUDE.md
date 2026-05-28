# CLAUDE.md

This file is configuration for [Claude Code](https://claude.ai/code) agents working in this repo (analogous to `.cursorrules` / `.aider.conf.yml`). Safe to ignore if you're not using Claude Code.

## Purpose

`tjsonl` is a community-maintained schema reference for the Claude Code transcript JSONL format. Two surfaces:

1. **`spec/`** — the v0.1 schema spec ([`transcript-schema-spec.md`](spec/transcript-schema-spec.md)). The machine-readable JSONSchema is bundled in the `tjsonl` package (installed path `tjsonl/_bundled/transcript-schema.json`; in this repo, [`src/tjsonl/_bundled/transcript-schema.json`](src/tjsonl/_bundled/transcript-schema.json)); `spec/README.md` cross-references it.
2. **`tj`** — a zero-dependency Python library + CLI under [`src/tjsonl/`](src/tjsonl/) that extracts, validates, and walks transcript jsonls.

Implementation history: [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381); the spec proposal it lifts from is in `vade-coo-memory/coo/instruments/_runs/2026-05-21_transcript-schema-extractor.md`.

## Layout

```
spec/
  transcript-schema-spec.md   ← canonical markdown spec
  README.md                   ← pointer to the bundled JSONSchema
src/tjsonl/
  __init__.py                 ← public API exports
  walk.py                     ← line-by-line iterator primitive
  extract.py                  ← observed-schema extractor
  validate.py                 ← spec validator
  cli.py                      ← `tj` CLI entry point
  _spec.py                    ← spec loader + derived constants
  _bundled/                   ← canonical JSONSchema (bundled into the package)
tests/
  fixtures/                   ← synthetic jsonl inputs
  test_walk.py / test_extract.py / test_validate.py / test_cli.py
  integration/test_session_start_resume.py   ← acceptance falsifier
```

## Running `tj`

After `pip install -e .`, the `tj` CLI is on PATH:

```bash
tj extract <session.jsonl>                     # observed-schema JSON to stdout
tj validate <session.jsonl>                    # exit 0 on clean; exit 1 on drift; 2 on invocation error
tj validate <session.jsonl> --spec custom.json # alternate spec
```

Without install, run via `PYTHONPATH=src python3 -m tjsonl.cli ...`.

## Tests

```bash
pip install -e ".[test]"
pytest                                         # unit + integration
pytest -m "not integration"                   # unit only
COO_TRANSCRIPTS_DIR=/path/to/cache pytest tests/integration -v
```

The integration test (the acceptance falsifier per [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381)) skips cleanly if no transcript directory is set. CI (see `.github/workflows/tj-tests.yml`) runs the unit suite across Python 3.10–3.13.

## When extending

- **Spec changes** follow `spec/transcript-schema-spec.md` §11 (versioning convention). Bump `schema_version` in both the markdown and the JSON; explain which rule fired (field-add / field-rename / new-type).
- **Library changes** keep the public API minimal — `walk`, `extract`, `validate`, `load_spec`. New shapes either fold into `extract`'s output or get their own subcommand on `cli`.
- **Contributors** see [CONTRIBUTING.md](CONTRIBUTING.md) for the three on-ramps (new attachment type, new tool, new event type).

## For VADE operators

The R2 ciphertext puller (`transcript-pull-local.py`) lives canonically in `vade-app/vade-runtime/scripts/` (private). It's not part of `tj` — `tj` operates on already-decrypted jsonls regardless of origin. Use `COO_TRANSCRIPTS_DIR=<path>` to point the integration test at any directory of `*.jsonl` files.

The repo uses a tracked pre-commit hook at [`hooks/pre-commit`](hooks/pre-commit) that hard-blocks any staged path ending in `.jsonl` (except `tests/fixtures/`, which are synthetic). Contributors don't need to enable it unless they're handling real transcripts in their working tree. Enable with:

```bash
git config core.hooksPath hooks
```

## Cross-references

- [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381) — implementation issue.
- [vade-coo-memory#864](https://github.com/vade-app/vade-coo-memory/pull/864) — merged spec proposal.
- [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) — community schema-stability ask.
