"""The app's own record of a run: a state word and a message in `runs/<run_id>/app_state.json`.

Everything else the UI shows (spend, stage, verdicts, the audit light) is read from the files the run already writes.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

FILE = "app_state.json"


def now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read(run_dir: Path) -> dict:
    path = run_dir / FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write(run_dir: Path, state: str, message: str | None) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    previous = read(run_dir)
    record = {
        "state": state,
        "message": message,
        "started_at": previous.get("started_at") or now(),
        "updated_at": now(),
    }
    (run_dir / FILE).write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record
