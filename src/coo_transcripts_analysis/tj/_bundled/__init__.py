"""Bundled package data — the JSONSchema spec ships here so it's importable
via `importlib.resources` from any install shape (editable, wheel, sdist).

The canonical path for external readers is `spec/transcript-schema.json` at
the repo root, which is a symlink to the file in this package so both paths
resolve to the same bytes.
"""
