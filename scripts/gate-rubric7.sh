#!/bin/bash
# Meridian gate hook: Increment 7 rubric (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_rubric7.py
