# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Tooling and a community-authored schema spec for the Claude Code transcript JSONL format. Two surfaces live here:

1. **`spec/`** — the v0.1 schema spec ([`transcript-schema-spec.md`](spec/transcript-schema-spec.md) + machine-readable [`transcript-schema.json`](spec/transcript-schema.json)). Observation-grounded; lifted from the merged proposal at [vade-coo-memory#864](https://github.com/vade-app/vade-coo-memory/pull/864).
2. **`tj`** — a thin Python library + CLI under [`src/coo_transcripts_analysis/tj/`](src/coo_transcripts_analysis/tj/) that extracts, validates, and walks transcript jsonls. Implementation issue: [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381).

There is also [`bin/transcript-pull-local.py`](bin/transcript-pull-local.py) — the operator's R2 → local-cache puller, vendored from `vade-app/vade-runtime`. It populates `transcripts/` for ad-hoc analysis and as the integration-test corpus.

## Layout

```
spec/
  transcript-schema-spec.md   ← canonical markdown spec
  transcript-schema.json      ← JSONSchema Draft 2020-12 rendering
src/coo_transcripts_analysis/
  __init__.py
  tj/
    __init__.py               ← public API exports
    walk.py                   ← line-by-line iterator primitive
    extract.py                ← observed-schema extractor
    validate.py               ← spec validator
    cli.py                    ← `tj` CLI entry point
    _spec.py                  ← spec loader + derived constants
tests/
  fixtures/                   ← synthetic jsonl inputs
  test_walk.py / test_extract.py / test_validate.py / test_cli.py
  integration/test_session_start_resume.py   ← acceptance falsifier
bin/
  transcript-pull-local.py    ← R2 → local-cache (operator tool, vendored)
transcripts/                  ← .gitignored cache (populated by the puller)
```

## Running `tj`

After `pip install -e .`, the `tj` CLI is on PATH:

```bash
tj extract <session.jsonl>                     # observed-schema JSON to stdout
tj validate <session.jsonl>                    # exit 0 on clean; exit 1 on drift
tj validate <session.jsonl> --spec custom.json # alternate spec
```

Without install, run via `PYTHONPATH=src python3 -m coo_transcripts_analysis.tj.cli ...`.

## Running the puller

```bash
./bin/transcript-pull-local.py                       # pull everything new
./bin/transcript-pull-local.py --prefix transcripts/2026/05/   # one month
./bin/transcript-pull-local.py -v                    # log each session (incl. skips)
```

Behavior to rely on:
- **Idempotent**: skips any `<id>.jsonl` already present with non-zero size. Re-pull by deleting the file.
- **Atomic per session**: download + decrypt happen in a tempdir, then `os.replace` onto the final path — an interrupted run never leaves half-written files in `transcripts/`.
- **Self-bootstrapping deps**: `uv` shebang pins `boto3`; you don't `pip install` separately.

### Prerequisites on the local machine

- `uv` on PATH (runs the puller script).
- `op` (1Password CLI) signed in (`eval $(op signin)`) or `OP_SERVICE_ACCOUNT_TOKEN` set. The script reads five `op://COO/...` refs for R2 creds + the age identity — see its docstring for the exact paths.
- `age` binary on PATH.

## Tests

```bash
pip install -e ".[test]"
pytest                                         # unit + integration
pytest -m "not integration"                   # unit only
COO_TRANSCRIPTS_DIR=/path/to/cache pytest tests/integration -v
```

The integration test (the acceptance falsifier per [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381)) skips cleanly if `transcripts/` is empty. CI (see `.github/workflows/tj-tests.yml`) runs the unit suite across Python 3.10–3.13.

## When extending

- **Spec changes** follow `spec/transcript-schema-spec.md` §11 (versioning convention). Bump `schema_version` in both the markdown and the JSON; explain which rule fired (field-add / field-rename / new-type).
- **Library changes** keep the public API minimal — `walk`, `extract`, `validate`, `load_spec`. New shapes either fold into `extract`'s output or get their own subcommand on `cli`.
- **The puller** (`bin/transcript-pull-local.py`) tracks the upstream copy in `vade-app/vade-runtime`. Don't drift; if changes are needed, file an issue upstream first.
- **Treat `transcripts/` as a read-only cache.** Anything derived (parsed indexes, per-session summaries, embeddings) belongs in a separate directory so `rm -rf transcripts/ && re-pull` stays cheap.

## Transcripts are sensitive

The pulled `<session>.jsonl` files are the redacted plaintext that lives in R2 — i.e. the rawest thing the storage tier holds. High-entropy strings are pre-redacted as `[REDACTED:high-entropy]`; assume any remaining content is intentional. Do not paste into external tools.

The repo uses a tracked pre-commit hook at [`hooks/pre-commit`](hooks/pre-commit) that hard-blocks any staged path under `transcripts/` or ending in `.jsonl` (except under `tests/fixtures/`, which are synthetic). Enable on a fresh clone with:

```bash
git config core.hooksPath hooks
```

## Cross-references

- [vade-app/vade-agent-logs#381](https://github.com/vade-app/vade-agent-logs/issues/381) — implementation issue.
- [vade-coo-memory#864](https://github.com/vade-app/vade-coo-memory/pull/864) — merged spec proposal.
- [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) — community schema-stability ask; engagement point post-merge.
