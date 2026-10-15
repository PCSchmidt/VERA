#!/bin/bash
# Meridian gate hook: Increment 9 check, part unsure (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --quiet python tools/checks/check_carry9.py --part unsure
