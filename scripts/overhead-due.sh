#!/bin/bash
# Run at the end of every session: says whether Meridian overhead hours are due for any day a gate passed since the
# last review gate, and how to log them. (The Increment 4 SPEC: logged per session, not once per increment.)
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
if uv run --no-project --quiet python tools/checks/check_dogfood.py; then
    echo "Overhead is logged for every gate day so far. If this session did Meridian work after the last entry, log it:"
fi
echo "  bash scripts/dogfood.sh overhead <hours> \"<dates and the Meridian work covered>\""
