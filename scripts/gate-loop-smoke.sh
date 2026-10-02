#!/bin/bash
# Meridian gate hook: a live smoke run of the loop reached the write-up with every call ledgered (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_loop_smoke.py smoke-006
