#!/bin/bash
# Meridian gate hook: audit v2 tested once on a fixed test split with the audit frozen (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_seeded_v2.py
