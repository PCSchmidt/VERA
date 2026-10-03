#!/bin/bash
# Meridian gate hook: the judge re-tested on this increment's claims and loop decisions, within its caps (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_retest3.py
