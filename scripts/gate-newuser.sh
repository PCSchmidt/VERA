#!/bin/bash
# Meridian gate hook: the new-user walkthrough is on record (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_newuser.py
