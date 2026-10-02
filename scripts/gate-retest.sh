#!/bin/bash
# Meridian gate hook: the judge re-test on real gate decisions is complete and honest (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_retest.py
