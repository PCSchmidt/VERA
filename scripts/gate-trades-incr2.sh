#!/bin/bash
# Meridian gate hook: T6, T7 and T9 decided in docs/04, and the generator comparison within its cap (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
for t in T6 T7 T9; do uv run --no-project --quiet python tools/checks/check_trade_decided.py $t || exit 2; done
exec uv run --no-project --quiet python tools/checks/check_generator_runs.py
