#!/bin/bash
# Meridian gate hook: lint and the test suite must pass (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
[ -f pyproject.toml ] || { echo "BLOCK: no pyproject.toml; the uv project does not exist yet" >&2; exit 2; }
uv run --quiet ruff check . || exit 2
uv run --quiet pytest -q || exit 2
