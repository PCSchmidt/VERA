#!/bin/bash
# Meridian gate hook: each topic scoped live, confirmed by a named person, scoping spend within the cap (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_scoping.py
