#!/bin/bash
# Meridian gate hook: a live run reached the final audit with every call ledgered (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_loop_smoke.py smoke-007 --through audit
