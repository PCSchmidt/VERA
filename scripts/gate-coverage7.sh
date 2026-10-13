#!/bin/bash
# Meridian gate hook: Increment 7 check, part coverage (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_carry7.py --part coverage
