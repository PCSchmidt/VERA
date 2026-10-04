#!/bin/bash
# Meridian gate hook: the second parent problem registered, reproduced, both harness variants built and costed (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_problem2.py
