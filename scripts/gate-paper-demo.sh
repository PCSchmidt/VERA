#!/bin/bash
# Meridian gate hook: papers made through the app from real reviews (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_paper_demo.py
