# spec/

This directory holds the human-readable schema spec for the Claude Code transcript JSONL format.

## Files

- **[`transcript-schema-spec.md`](transcript-schema-spec.md)** — the source-of-truth, observation-grounded spec (markdown).

## Machine-readable JSONSchema

The JSONSchema (Draft 2020-12) rendering of the spec is bundled in the `tjsonl` package so it loads via `importlib.resources` in any install shape (editable, wheel, sdist, zipapp). After `pip install tjsonl` the package path is `tjsonl/_bundled/transcript-schema.json`; in this repository the file is at [`src/tjsonl/_bundled/transcript-schema.json`](../src/tjsonl/_bundled/transcript-schema.json).

For downstream consumers that want the raw JSONSchema without installing the package, fetch it directly from GitHub:

<https://raw.githubusercontent.com/vade-app/tjsonl/main/src/tjsonl/_bundled/transcript-schema.json>

Or, from Python:

```python
from tjsonl import load_spec
schema = load_spec()  # returns the parsed JSONSchema dict
```

The `$id` inside the schema is the stable canonical URL.
