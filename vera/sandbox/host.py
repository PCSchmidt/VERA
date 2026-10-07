"""The two process calls the app makes on the user's own machine, kept with the other process handling (FND-F-03).

Neither runs model-written code: `docker_available` asks the Docker CLI whether a daemon answers, and `spawn_worker`
starts the app's own worker module with a fixed argument list. Model-written code runs only through
`vera.sandbox.run_script`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=8, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def spawn_worker(run_id: str, phase: str, *, cwd: Path, env: dict[str, str], log: Path) -> None:
    """Start `python -m vera.app.worker <run_id> <phase>` detached from the server, output to `log`."""
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0  # outlives the server's console
    with log.open("ab") as out:
        subprocess.Popen(  # noqa: S603 - fixed argv; the run id was validated
            [sys.executable, "-m", "vera.app.worker", run_id, phase],
            cwd=cwd, env=env, stdout=out, stderr=out, creationflags=flags,
        )  # fmt: skip
