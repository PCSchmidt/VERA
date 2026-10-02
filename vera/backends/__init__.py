"""Judge backends (P2). Vendor model SDKs may be imported only inside this package (FND-C-01).

Each backend implements `JudgeBackend.ask(state, questions)` and makes every
model call through `vera.ledger.metered_call`, so each call is budgeted and
recorded (FND-F-01).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
RETRY_STATUS = {429, 502, 503, 504}


def post_with_retry(client: httpx.Client, url: str, *, tries: int = 4, **kwargs) -> httpx.Response:
    """POST, retrying transport failures (this machine has intermittent DNS failures) and 429/502/503/504.

    Runs inside one metered call, so the ledger sees one record whose latency includes the waits. After the last
    attempt the final response is returned (the caller reports its error) or the transport error is raised.
    """
    for attempt in range(tries):
        try:
            resp = client.post(url, **kwargs)
        except httpx.TransportError:
            if attempt == tries - 1:
                raise
        else:
            if resp.status_code not in RETRY_STATUS or attempt == tries - 1:
                return resp
        time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


def api_key(name: str, env_file: Path | None = None) -> str:
    """The key from the environment, else from the repo's git-ignored .env. Raises if missing."""
    if os.environ.get(name):
        return os.environ[name]
    path = env_file or ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name and value.strip():
                return value.strip().strip('"').strip("'")
    raise KeyError(f"{name} is not set (environment or .env)")
