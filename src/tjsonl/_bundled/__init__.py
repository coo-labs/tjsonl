"""Bundled package data — the JSONSchema spec ships here so it's importable
via `importlib.resources` from any install shape (editable, wheel, sdist).

This is the canonical location for the machine-readable schema. External
readers without the package installed can fetch the raw JSON from GitHub:

    https://raw.githubusercontent.com/coo-labs/tjsonl/main/src/tjsonl/_bundled/transcript-schema.json

The human-readable markdown spec is not shipped in the wheel; it lives in
the repository at `spec/transcript-schema-spec.md` (fetch it from GitHub if
you only have the installed package).
"""
