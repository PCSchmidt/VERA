"""Keep the machine awake while a long run is in progress (Windows; a no-op elsewhere).

Found in Increment 2: Windows entered Modern Standby for 39 minutes in the middle of a multi-run comparison. The
processes froze, and when the machine woke the sandbox's wall-clock limits and the runs' wall budgets had jumped past
their limits, so valid experiments were recorded as timed out. The request lasts only as long as the process, changes
no system setting, and does not stop the display from turning off or the lid from sleeping the machine: a run that
must survive a closed lid still needs the user's power settings.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextmanager
def keep_awake() -> Iterator[bool]:
    """Ask Windows not to sleep for the duration of the block. Yields True if the request was made."""
    if sys.platform != "win32":
        yield False
        return
    import ctypes  # noqa: PLC0415

    previous = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        yield previous != 0
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)  # release: back to the default
