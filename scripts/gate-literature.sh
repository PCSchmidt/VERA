#!/bin/bash
# Meridian gate hook: each topic has a literature section whose every claim carries a quote found in its source (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_literature.py
