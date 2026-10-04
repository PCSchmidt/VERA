#!/bin/bash
# Meridian gate hook: the registered protocol, its ground truth check and one live run (exit 2 blocks).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
exec uv run --no-project --quiet python tools/checks/check_protocol.py
