#!/bin/bash
# Meridian gate hook: the T8 entry is complete (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_t8.py
