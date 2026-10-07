#!/bin/bash
# Meridian gate hook: app check, part core (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_app.py --part core
