# ruff: noqa: E501
"""The walkthrough gate refuses a template, a coached session, an unfinished run and an over-cap spend, and accepts a real record."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "checks" / "check_newuser.py"


def good(tmp: Path, **change) -> Path:
    rec = {"person": "PhD student, ML", "independent_of_builder": True, "setup": "fresh clone, Windows laptop",
           "observer": "Chris", "coached": False, "key_provided_by": "the maintainer, small credit",
           "started_at": "2026-10-09T10:00:00Z", "first_run_started_at": "2026-10-09T10:20:00Z", "finished_at": "2026-10-09T10:41:00Z",
           "run_id": "walk-1", "confusions": [{"at": "00:07", "where": "connect key", "what": "did not see the button", "observer_helped": False}],
           "answers": {"whose_money_and_how_they_know": "mine, the page said so", "trusted_the_spend_display_and_why": "yes, it moved",
                       "review_worth_reading_and_what_better": "yes; more sources", "what_would_stop_them_using_it": "setup time"},
           "notes": ""} | change  # fmt: skip
    d = tmp / "data" / "walkthrough"
    (d / "walk-1").mkdir(parents=True)
    (d / "record.json").write_text(json.dumps(rec), encoding="utf-8")
    ev = d / "walk-1"
    (ev / "app_request.json").write_text(json.dumps({"max_usd": 1.0}), encoding="utf-8")
    (ev / "app_state.json").write_text(json.dumps({"state": "complete"}), encoding="utf-8")
    (ev / "literature.md").write_text("## Literature review\n", encoding="utf-8")
    (ev / "audit_report.json").write_text(json.dumps({"overall": "green"}), encoding="utf-8")
    (ev / "ledger.jsonl").write_text(json.dumps({"cost_usd": 0.2}) + "\n", encoding="utf-8")
    return tmp


def run(tmp: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK), "--root", str(tmp)], capture_output=True, text=True)


def test_a_real_record_passes_and_reports_the_session(tmp_path: Path) -> None:
    out = run(good(tmp_path))
    assert (
        out.returncode == 0
        and "independent walkthrough by PhD student, ML" in out.stdout
        and "21 minutes" in out.stdout
    )


@pytest.mark.parametrize("change, why", [
    ({"coached": True}, "coached"), ({"independent_of_builder": "yes"}, "independent_of_builder"),
    ({"person": "a first name or a role"}, "template"), ({"answers": {"whose_money_and_how_they_know": ""}}, "four answers"),
    ({"first_run_started_at": "2026-10-09T09:00:00Z"}, "order"),
])  # fmt: skip
def test_a_bad_record_is_refused(tmp_path: Path, change: dict, why: str) -> None:
    out = run(good(tmp_path, **change))
    assert out.returncode == 2 and "BLOCK" in out.stderr, why


def test_an_unfinished_or_over_cap_run_is_refused(tmp_path: Path) -> None:
    good(tmp_path)
    ev = tmp_path / "data" / "walkthrough" / "walk-1"
    (ev / "app_state.json").write_text(json.dumps({"state": "stopped"}), encoding="utf-8")
    assert run(tmp_path).returncode == 2
    (ev / "app_state.json").write_text(json.dumps({"state": "complete"}), encoding="utf-8")
    (ev / "ledger.jsonl").write_text(json.dumps({"cost_usd": 1.5}) + "\n", encoding="utf-8")
    assert "over the cap" in run(tmp_path).stderr
