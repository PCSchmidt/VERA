# ruff: noqa: E501
"""check_dogfood: a note that starts with the day it covers credits that day; entries before the increment still do not count."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "tools" / "checks" / "check_dogfood.py"


def run(tmp_path: Path, entries: list[dict]) -> subprocess.CompletedProcess:
    (tmp_path / ".meridian").mkdir()
    tele = [
        {"timestamp": "2026-10-01T10:00:00Z", "event_type": "gate_passed", "gate": "incr3_review"},
        {"timestamp": "2026-10-03T10:00:00Z", "event_type": "gate_passed", "gate": "a"},
        {"timestamp": "2026-10-05T10:00:00Z", "event_type": "gate_passed", "gate": "b"},
    ]
    (tmp_path / ".meridian" / "telemetry.jsonl").write_text("".join(json.dumps(e) + "\n" for e in tele), encoding="utf-8")
    (tmp_path / ".meridian" / "dogfood.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return subprocess.run([sys.executable, str(CHECK), "--root", str(tmp_path)], capture_output=True, text=True)


def entry(at: str, note: str, hours: float = 5) -> dict:
    return {"type": "overhead", "recorded_at": at, "hours": hours, "note": note}


def test_an_entry_recorded_later_for_a_named_day_credits_that_day(tmp_path: Path) -> None:
    done = run(tmp_path, [entry("2026-10-04T11:00:00Z", "2026-10-03: carry-in"), entry("2026-10-05T12:00:00Z", "2026-10-05: review")])
    assert done.returncode == 0, done.stdout + done.stderr


def test_without_the_date_the_recorded_day_is_what_counts(tmp_path: Path) -> None:
    done = run(tmp_path, [entry("2026-10-04T11:00:00Z", "carry-in"), entry("2026-10-05T12:00:00Z", "review")])
    assert done.returncode == 2 and "2026-10-03" in done.stdout + done.stderr


def test_an_entry_recorded_before_the_increment_opened_never_counts(tmp_path: Path) -> None:
    done = run(tmp_path, [entry("2026-09-30T11:00:00Z", "2026-10-03: too early"), entry("2026-10-05T12:00:00Z", "2026-10-05: x")])
    assert done.returncode == 2
