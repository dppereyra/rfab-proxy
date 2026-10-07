# AGENTS.md

Guidance for coding agents working in rfab-proxy.

## Setup

Tool versions (Python 3.14 and 3.15, uv, tox with tox-uv, Trivy, Helm, MkDocs) are pinned in
`mise.toml`. From a fresh checkout:

```bash
mise install
```

`mise.toml` is the single source of truth for versions. CI reads the Python matrix and the uv
version from it through `mise run ci:versions`. To add or drop a Python version, change
`mise.toml` and add the matching env to `tox.ini`.

## Layout

- `src/rfab_proxy/`: the application package
- `tests/`: the test suite, with files named `tests-*.py`
- `scripts/`: repository tooling that is not part of the package

## Working rules

- Write the failing test before the implementation.
- `uv.lock` is the source of truth for dependencies. Update it with `uv lock` whenever
  `pyproject.toml` changes.
