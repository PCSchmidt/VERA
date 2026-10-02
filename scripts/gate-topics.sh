#!/bin/bash
# Meridian gate hook: three topics with hashed key-paper lists, recorded before any retrieval (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_topics.py
