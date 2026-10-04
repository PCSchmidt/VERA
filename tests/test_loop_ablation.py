"""RSH-F-04, the ablation stage, demonstrated with a scripted generator whose idea provably helps (docs/02 D).

The winner is C1 (lower residual than the baseline on both datasets); its two ablations are scripted: removing the
first component loses most of the gain, removing the second loses none. A run with no winner runs no ablation.
No network.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.loop_fakes import FakeGenerator, FakeSandbox, ds, make_deps
from vera.loop import tables
from vera.loop.graph import run_loop

ABLATION_RESULTS = {
    "A1": {"analytical": ds(2.3), "airfoil": ds(4.5)},  # without the first component: nearly back to the baseline
    "A2": {"analytical": ds(1.8), "airfoil": ds(2.2)},  # without the second: the same as the full idea
}


def sandbox_with_ablations() -> FakeSandbox:
    from tests.loop_fakes import IDEA_RESULTS

    return FakeSandbox(ideas={**IDEA_RESULTS, **ABLATION_RESULTS})


def test_RSH_F_04_the_winning_idea_is_ablated_and_the_variants_join_the_results(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, sandbox=sandbox_with_ablations())
    deps.generator = FakeGenerator(deps.ledger, deps.budget, ablate=True)
    state = run_loop(deps)
    assert state.get("stop") is None
    assert "ablation" in state["trail"]
    labels = [m for m in state["results"] if " without " in m]
    assert labels == ["C1: shared knots without shared knots", "C1: shared knots without refit step"]
    base = state["results"][tables.BASELINE]["analytical"]["residual_mse_pct"]["mean"]
    cut = state["results"][labels[0]]["analytical"]["residual_mse_pct"]["mean"]
    same = state["results"][labels[1]]["analytical"]["residual_mse_pct"]["mean"]
    assert cut > same and abs(cut - base) < abs(same - base)  # the first component carried the gain
    record = json.loads((deps.run_dir / "artifacts" / "ablation.json").read_text(encoding="utf-8"))
    assert record["ran"] is True and record["idea"] == "C1: shared knots" and all(v["ok"] for v in record["variants"])
    paper = (deps.run_dir / "paper.md").read_text(encoding="utf-8")
    assert "without shared knots" in paper  # the variants are rows of the results table the paper carries


def test_RSH_F_04_no_winner_means_no_ablation_and_the_reason_is_recorded(tmp_path: Path) -> None:
    losing = {"C1": {"analytical": ds(2.9), "airfoil": ds(5.0)}, "C2": {"analytical": ds(3.1), "airfoil": ds(5.2)}}
    deps = make_deps(tmp_path, sandbox=FakeSandbox(ideas=losing))
    state = run_loop(deps)
    assert "ablation" not in state["trail"] and not any(" without " in m for m in state["results"])
    record = json.loads((deps.run_dir / "artifacts" / "ablation.json").read_text(encoding="utf-8"))
    assert record["ran"] is False and "no idea beat the baseline" in record["reason"]
    assert "p3.ablation" not in deps.generator.calls
