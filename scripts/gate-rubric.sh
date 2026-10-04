#!/bin/bash
# Meridian gate hook: outputs scored by a person, blind, before the independent scorer; claim re-labels exist (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_rubric.py
