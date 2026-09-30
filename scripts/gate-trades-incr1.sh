#!/bin/bash
# Meridian gate hook: T1 and T2 decided in docs/04 (exit 2 blocks). See tools/checks/check_trade_decided.py.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
uv run --no-project --quiet python tools/checks/check_trade_decided.py T1 || exit 2
exec uv run --no-project --quiet python tools/checks/check_trade_decided.py T2
