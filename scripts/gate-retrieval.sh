#!/bin/bash
# Meridian gate hook: three topics retrieved live, recall measured, relevance screen checked by the user (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_retrieval.py
