"""The Increment 5 rubric gate: a person, blind, earlier than the independent scorer, and not a copy."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "tools" / "checks" / "check_rubric5.py"
CRIT = ("answers_question", "coverage", "correctness", "reproducibility", "honesty")


def entry(out: str, at: str, nums: tuple, blind: bool = True) -> dict:
    return {"output": out, "at": at, "blind": blind, "note": "", "scores": dict(zip(CRIT, nums, strict=True))}


def write(tmp: Path, human: list, indep: list, by: str = "Chris") -> subprocess.CompletedProcess:
    d = tmp / "data" / "results"
    d.mkdir(parents=True, exist_ok=True)
    (d / "rubric5_chris.json").write_text(json.dumps({"by": by, "entries": human}), encoding="utf-8")
    (d / "rubric5_evaluator.json").write_text(json.dumps({"by": "evaluator", "entries": indep}), encoding="utf-8")
    return subprocess.run([sys.executable, str(CHECK), "--root", str(tmp)], capture_output=True, text=True)


H = [entry(o, "2026-10-10T10:00:00Z", (4, 3, 4, 4, 5)) for o in ("W1", "R1", "R2")]
I = [entry(o, "2026-10-10T11:00:00Z", (3, 2, 4, 4, 4), blind=False) for o in ("W1", "R1", "R2")]


def test_a_blind_human_scoring_before_the_independent_scorer_passes(tmp_path: Path) -> None:
    out = write(tmp_path, H, I)
    assert out.returncode == 0 and "3 outputs scored blind by Chris" in out.stdout


def test_refused_when_not_blind_late_copied_incomplete_or_not_a_person(tmp_path: Path) -> None:
    assert write(tmp_path, [{**e, "blind": False} for e in H], I).returncode == 2
    assert (
        write(tmp_path, [{**e, "at": "2026-10-10T12:00:00Z"} for e in H], I).returncode == 2
    )  # after the independent file began
    assert (
        write(tmp_path, H, [{**e, "scores": h["scores"]} for e, h in zip(I, H, strict=True)]).returncode == 2
    )  # a copy
    assert write(tmp_path, H[:2], I).returncode == 2  # one output unscored
    assert write(tmp_path, H, I, by="Claude").returncode == 2
