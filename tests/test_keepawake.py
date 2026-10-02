"""The keep-awake request is made on Windows, released afterwards, and is a harmless no-op elsewhere."""

from __future__ import annotations

import sys

from vera.keepawake import keep_awake


def test_keep_awake_is_a_context_manager_that_never_raises() -> None:
    with keep_awake() as requested:
        assert requested in (True, False)
        if sys.platform != "win32":
            assert requested is False
    with keep_awake():  # and can be entered again after release
        pass
