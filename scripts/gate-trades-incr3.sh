#!/bin/bash
# Meridian gate hook: T3, T5, T7 and T10 decided in docs/04, and the spend so far within the caps (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
for t in T3 T5 T7 T10; do uv run --no-project --quiet python tools/checks/check_trade_decided.py $t || exit 2; done
exec bash scripts/gate-ledger.sh
