#!/bin/bash
# Meridian gate hook: one complete end-to-end run (a runs/loop-* attempt) inside its budget, honestly recorded (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_run.py --prefix loop-
