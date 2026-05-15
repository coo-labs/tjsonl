# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Side project for fetching and analyzing Claude Code session transcripts from remote sessions working in the **vade-app** GitHub org and its repositories. Currently in initial state — the pull/decrypt pipeline exists; concrete analysis goals are TBD.

## Layout

- `bin/transcript-pull-local.py` — the one script. Downloads ciphertext from R2, decrypts via `age`, gunzips, lands `<session_id>.jsonl` in `transcripts/`. Vendored from `vade-app/vade-runtime/scripts/transcript-pull-local.py` — keep that lineage in mind before adding repo-specific divergence.
- `transcripts/` — decrypted plaintext JSONL, one file per session. ~160 files currently. **Redacted but still sensitive** (this is the rawest form the storage tier holds — see script docstring). Do not commit transcripts; do not paste contents into external tools.

## Running the puller

```bash
./bin/transcript-pull-local.py                       # pull everything new
./bin/transcript-pull-local.py --prefix transcripts/2026/05/   # one month
./bin/transcript-pull-local.py -v                    # log each session (incl. skips)
```

Behavior to rely on:
- **Idempotent**: skips any `<id>.jsonl` already present with non-zero size. Re-pull by deleting the file.
- **Atomic per session**: download + decrypt happen in a tempdir, then `os.replace` onto the final path — an interrupted run never leaves half-written files in `transcripts/`.
- **Self-bootstrapping deps**: `uv` shebang pins `boto3`; you don't `pip install`.

### Prerequisites on the local machine

- `uv` on PATH (runs the script).
- `op` (1Password CLI) signed in (`eval $(op signin)`) or `OP_SERVICE_ACCOUNT_TOKEN` set. The script reads five `op://COO/...` refs for R2 creds + the age identity — see the docstring for the exact paths.
- `age` binary on PATH.

The `_preflight` check enforces `op` and `age`; missing tools fail fast with a clear message.

## Transcript format

Each line is one JSON event from a Claude Code session. Top-level `type` discriminates (`attachment`, `user`, `assistant`, tool results, etc.). Useful fields when slicing: `sessionId`, `timestamp`, `cwd`, `gitBranch`, `parentUuid`/`uuid` (threading), `isSidechain` (sub-agent calls), `version` (CC version), and hook payloads under `attachment`. High-entropy strings are pre-redacted as `[REDACTED:high-entropy]` — assume any remaining content is intentional.

## When extending

- Analysis code should be additive — new scripts/notebooks alongside `bin/transcript-pull-local.py`, not edits to it (it tracks an upstream).
- Treat `transcripts/` as a read-only cache. Anything derived (parsed indexes, per-session summaries, embeddings) belongs in a separate directory so a `rm -rf transcripts/ && re-pull` stays cheap.
