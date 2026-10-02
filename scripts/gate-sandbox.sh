#!/bin/bash
# Meridian gate hook: the sandbox checks (exit 2 blocks). Docker must be running: the sandbox tests do not skip here.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
uv run --no-project --quiet python tools/checks/check_sandbox_use.py || exit 2
export VERA_REQUIRE_DOCKER=1
exec uv run --quiet pytest -q tests/test_sandbox.py
