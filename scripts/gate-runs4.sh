#!/bin/bash
# Meridian gate hook: the two end-to-end runs reached their final stage, ledgers equal, verdicts from others, papers committed (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_runs4.py
