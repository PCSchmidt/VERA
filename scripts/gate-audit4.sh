#!/bin/bash
# Meridian gate hook: the v3 audit tested once on the seeded set and the novelty gold set, with the audit frozen (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
uv run --no-project --quiet python tools/checks/check_seeded_v3.py || exit 2
exec uv run --no-project --quiet python tools/checks/check_novelty_gold.py
