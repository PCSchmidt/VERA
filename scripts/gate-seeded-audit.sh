#!/bin/bash
# Meridian gate hook: the audit's seeded-fault evidence is complete and the test split unchanged (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_seeded.py
