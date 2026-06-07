# _bundled/ — canonical JSONSchema (do not hand-edit casually)

`transcript-schema.json` is the canonical machine-readable schema bundled into the `tjsonl` package. The markdown spec at `../../../spec/transcript-schema-spec.md` is the human-facing pair.

**Schema changes require version bump per spec §11.** Bump `schema_version` in BOTH the markdown spec and this JSON file. Cite which rule fired in the commit: field-add / field-rename / new-type.

Tests must pass after any edit:
```sh
pytest tests/test_validate.py tests/test_extract.py
```

The integration falsifier (`tests/integration/test_session_start_resume.py`) skips cleanly unless `COO_TRANSCRIPTS_DIR` is set — point it at a directory of real (decrypted) jsonls to exercise the round-trip.

Public API surface: `walk`, `extract`, `validate`, `load_spec` (see `../__init__.py`). New shapes either fold into `extract`'s output or get a `cli.py` subcommand.

---

*If you notice contradictions between the substrate and this file, update it after finishing your current task.*
