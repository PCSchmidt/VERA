"""Judge backends (P2). Vendor model SDKs may be imported only inside this package (FND-C-01).

Each backend implements `JudgeBackend.ask(state, questions)` and makes every
model call through `vera.ledger.metered_call`, so each call is budgeted and
recorded (FND-F-01).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
