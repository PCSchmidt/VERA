#!/bin/bash
# Meridian gate hook: Increment 10 check, part sticky (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --quiet python tools/checks/check_carry10.py --part sticky
