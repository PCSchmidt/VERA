#!/bin/bash
# Meridian gate hook: the fresh topic's key papers fixed and hashed before any retrieval for it (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_topics.py --expect 4
