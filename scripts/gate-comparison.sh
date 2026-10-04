#!/bin/bash
# Meridian gate hook: the ScientistTwo comparison made under a protocol hashed first (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_comparison.py
