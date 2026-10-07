"""Degenerate spread (Increment 5 carry-in): an idea whose replications do not vary while the baseline's do."""

from __future__ import annotations

import json
from pathlib import Path

from tests.loop_fakes import BASELINE_OK, FakeSandbox, ds, make_deps
from vera.graph import run  # noqa: F401
from vera.loop.graph import run_loop
from vera.loop.spread import degenerate_spread


def cell(mean: float, std: float, n: int = 100) -> dict:
    return {"mean": mean, "std": std, "values": [mean] * n}


def result(**cells: dict) -> dict:
    return {"valid": True, "d1": {"valid": True, **cells}}["d1"]


def test_a_planted_near_zero_spread_is_flagged_against_a_baseline_that_varies() -> None:
    baseline = {"cal": result(mae=cell(10.68, 0.70))}
    flagged = {"cal": result(mae=cell(24.612, 1.27e-13))}  # the credal run's idea C1
    reasons = degenerate_spread(flagged, baseline)
    assert len(reasons) == 1 and "cal mae" in reasons[0] and "does not respond to the data" in reasons[0]


def test_ordinary_spread_few_replications_and_a_deterministic_baseline_are_not_flagged() -> None:
    baseline = {"cal": result(mae=cell(10.68, 0.70))}
    assert degenerate_spread({"cal": result(mae=cell(9.9, 0.4))}, baseline) == []  # varies like the baseline
    assert degenerate_spread({"cal": result(mae=cell(24.6, 1e-13, n=5))}, baseline) == []  # too few to say
    still = {"cal": result(mae=cell(10.68, 0.0))}
    assert degenerate_spread({"cal": result(mae=cell(24.6, 1e-13))}, still) == []  # nothing to compare with
    assert degenerate_spread({"cal": {"valid": False}}, baseline) == []  # an invalid dataset is another rule's


def flat(mean: float, std: float) -> dict:
    out = ds(mean, std)
    for k in ("residual_mse_pct", "residual_in_sample_pct"):
        out[k]["values"] = [out[k]["mean"]] * 20
    return out


def test_a_degenerate_idea_run_is_retried_with_the_reason_and_dropped_if_it_stays_flat(tmp_path: Path) -> None:
    baseline = {"analytical": flat(2.4, 0.3), "airfoil": flat(4.7, 0.5)}
    stuck = {"analytical": flat(3.0, 1e-13), "airfoil": flat(5.0, 1e-13)}
    ok = {"analytical": flat(1.8, 0.2), "airfoil": flat(2.2, 0.3)}
    ideas = {"C1": [stuck, ok], "C2": [stuck, stuck]}  # C1 is fixed on the retry; C2 stays flat and is dropped
    deps = make_deps(tmp_path, sandbox=FakeSandbox(baseline={**BASELINE_OK, **baseline}, ideas=ideas))
    state = run_loop(deps)
    assert list(state["results"]) == ["TreeHFD (baseline)", "C1: shared knots"]
    log = json.loads((deps.run_dir / "artifacts" / "subset_exp.json").read_text(encoding="utf-8"))["log"]
    assert "degenerate spread" in log["C1: shared knots"]["attempts"][0]["error"]
    assert log["C2: ridge leaves"]["ok"] is False
