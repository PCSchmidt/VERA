#!/bin/bash
# Meridian gate hook: Increment 8 re-audits (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --quiet python tools/checks/check_reaudit8.py
