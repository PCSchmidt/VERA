#!/bin/bash
# Meridian gate hook: runs a VERA Python check (exit 2 blocks). See tools/checks/.
cd "$(dirname "${BASH_SOURCE[0]}")/.." && exec uv run --no-project --quiet python tools/checks/check_schema_version.py
