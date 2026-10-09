#!/bin/bash
# Meridian gate hook: Increment 5 rubric scores by a named human, blind, earlier than the independent scorer (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_rubric5.py
