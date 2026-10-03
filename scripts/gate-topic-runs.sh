#!/bin/bash
# Meridian gate hook: three topics run to their final stage, costs measured, one carried through the loop (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_topic_runs.py
