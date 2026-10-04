#!/bin/bash
# Meridian gate hook: literature stage v2 measured, fresh reviews committed with their retrieval statement (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_lit2.py
