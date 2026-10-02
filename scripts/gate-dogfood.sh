#!/bin/bash
# Meridian gate hook: Meridian overhead hours were logged for every day a gate passed this increment (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_dogfood.py "$@"
