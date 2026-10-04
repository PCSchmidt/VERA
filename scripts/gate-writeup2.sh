#!/bin/bash
# Meridian gate hook: paper shape, figures matching their cells, ablation stage demonstrated (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_writeup2.py
