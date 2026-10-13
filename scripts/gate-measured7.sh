#!/bin/bash
# Meridian gate hook: Increment 7 check, part measured (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --quiet python tools/checks/check_carry7.py --part measured
