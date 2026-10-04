"""RSH-F-02, RSH-F-03: the loop's baseline and idea stages, gated, with fake judge, generator, sandbox.

No network.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.loop_fakes import (
    BASELINE_OFF,
    TARGET,
    FakeGenerator,
    FakeJudge,
    FakeSandbox,
    ds,
    make_deps,
    make_spec,
    paper,
)
from vera.graph import run, run_config, sqlite_checkpointer
from vera.ledger import Ledger
from vera.loop import questions, tables
from vera.loop.graph import build_graph, run_loop
from vera.schemas import SelfGradingError, StageResult

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).with_name("_loop_worker.py")


def gates(deps) -> list[dict]:
    return [json.loads(ln) for ln in (deps.run_dir / "gates.jsonl").read_text(encoding="utf-8").splitlines()]


# ── RSH-F-02: nothing starts before the baseline is accepted ───────────────────────────────────────


def test_RSH_F_02_a_rejected_baseline_stops_the_run_before_any_idea(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, sandbox=FakeSandbox(baseline=BASELINE_OFF))  # airfoil 4.7 vs 2.0 +- 1.0
    state = run_loop(deps)
    assert state["stop"]["stage"] == "baseline" and "not reproduced" in state["stop"]["reason"]
    assert deps.generator.calls == []  # no idea was generated
    assert state["trail"] == ["baseline", "baseline_gate"]
    (sr,) = [StageResult.model_validate(s) for s in state["stage_results"]]
    assert (sr.stage, sr.decision) == ("baseline", "reject")
    assert gates(deps)[0]["shadow_answer"] is False  # and the programmatic check agrees with the verdict
    report = json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))
    assert report["stage_reached"] == "baseline" and report["stop_reason"].startswith("gate:")
    assert report["stages_completed"] == []  # a rejected stage is not a completed one


def test_RSH_F_02_a_baseline_run_that_fails_stops_the_run(tmp_path: Path) -> None:
    sandbox = FakeSandbox()
    sandbox.fail_baseline = True
    deps = make_deps(tmp_path, sandbox=sandbox)
    state = run_loop(deps)
    assert "baseline run failed" in state["stop"]["reason"] and deps.generator.calls == []


def test_RSH_F_02_a_rule_decides_the_baseline_gate_not_an_unsure_or_wrong_judge(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, judge=FakeJudge(confidence=0.5, overrides={"loop.baseline_reproduced": False}))
    state = run_loop(deps)
    assert "baseline_gate" in state["trail"] and state["verdicts"]["baseline"]["backend"] == "rule"
    first = gates(deps)[0]
    assert first["verdict"]["answer"] is True and first["judge_verdict"]["answer"] is False  # the judge's miss is kept


def test_RSH_F_02_an_unsure_judge_where_no_rule_exists_fails_closed(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, judge=FakeJudge(low_confidence_for={"loop.guidance_met"}))
    state = run_loop(deps)
    assert state["stop"]["stage"] == "write_up" and state["stop"]["reason"].startswith("gate:")


def test_RSH_F_02_an_accepted_baseline_runs_every_idea_stage(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    state = run_loop(deps)
    assert state.get("stop") is None
    assert state["trail"] == ["baseline", "baseline_gate", "ideate", "screen", "subset_exp", "results_gate", "ablation",
                              "write_up", "writeup_gate", "audit"]  # a winner exists, so the ablation stage ran

    assert [i["name"] for i in state["ideas"]] == ["C1: shared knots", "C2: ridge leaves", "C3: pruned pairs",
                                                   "C4: deeper variables"]  # fmt: skip
    assert state["selected"] == ["C1: shared knots", "C2: ridge leaves"]  # scores 5 and 4; 3 and 2 not both kept
    assert state["best"] == "C1: shared knots"  # beats the baseline on both datasets; C2 loses on one
    stages = [StageResult.model_validate(s) for s in state["stage_results"]]
    assert [(s.stage, s.decision) for s in stages] == [("baseline", "accept"), ("ideate", "accept"),
                                                       ("subset_exp", "accept"), ("write_up", "accept"),
                                                       ("audit", "accept")]  # fmt: skip
    assert deps.budget.spent_usd == pytest.approx(deps.ledger.total_cost())  # one ledger, one budget
    report = json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))
    assert report["stop_reason"] == "completed"
    assert report["stages_completed"] == ["baseline", "ideate", "subset_exp", "write_up", "audit"]


def test_RSH_F_02_ideas_below_the_bar_are_not_run(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, judge=FakeJudge(scores={"C1": 2, "C2": 1, "C3": 2, "C4": 1}))
    state = run_loop(deps)
    assert state["stop"]["stage"] == "ideate" and "scored 3 or more" in state["stop"]["reason"]
    assert "p3.subset_exp" not in deps.generator.calls  # nothing was implemented


def test_RSH_F_02_idea_experiments_get_one_retry_then_are_dropped(tmp_path: Path) -> None:
    ideas = {"C1": [{"error": "NameError: x"}, {"analytical": ds(1.8), "airfoil": ds(2.2)}],  # fixed on retry
             "C2": [{"error": "boom"}, {"error": "boom again"}]}  # fails both times: excluded  # fmt: skip
    deps = make_deps(tmp_path, sandbox=FakeSandbox(ideas=ideas))
    state = run_loop(deps)
    assert list(state["results"]) == ["TreeHFD (baseline)", "C1: shared knots"]
    log = json.loads((deps.run_dir / "artifacts" / "subset_exp.json").read_text(encoding="utf-8"))["log"]
    assert [a["error"] is None for a in log["C1: shared knots"]["attempts"]] == [False, True]
    assert log["C2: ridge leaves"]["ok"] is False and len(log["C2: ridge leaves"]["attempts"]) == 2
    assert deps.generator.calls.count("p3.subset_exp") == 4  # 2 ideas x 2 attempts


def test_RSH_F_02_no_valid_idea_run_stops_the_run(tmp_path: Path) -> None:
    ideas = {k: {"error": "boom"} for k in ("C1", "C2")}
    state = run_loop(make_deps(tmp_path, sandbox=FakeSandbox(ideas=ideas)))
    assert state["stop"]["stage"] == "subset_exp" and "valid run" in state["stop"]["reason"]


def test_RSH_F_02_an_idea_whose_reply_has_no_code_is_retried(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.no_code = {"C2"}
    state = run_loop(deps)
    assert "C2: ridge leaves" not in state["results"] and state["best"] == "C1: shared knots"


def test_RSH_F_02_when_no_idea_beats_the_baseline_the_stage_is_rejected_not_hidden(tmp_path: Path) -> None:
    ideas = {"C1": {"analytical": ds(2.6), "airfoil": ds(3.0)}, "C2": {"analytical": ds(2.9), "airfoil": ds(2.6)}}
    state = run_loop(make_deps(tmp_path, sandbox=FakeSandbox(ideas=ideas)))
    assert state.get("stop") is None and state["best"] is None  # a negative result is a result
    decisions = {StageResult.model_validate(s).stage: s["decision"] for s in state["stage_results"]}
    assert decisions["subset_exp"] == "reject" and decisions["write_up"] == "accept"  # the write-up reports it


def test_RSH_F_02_the_results_gate_is_decided_by_rules_whatever_the_judge_says(tmp_path: Path) -> None:
    wrong = {"loop.beats_baseline": False, "loop.best_method": "TreeHFD (baseline)"}
    deps = make_deps(tmp_path, judge=FakeJudge(low_confidence_for={"loop.best_method"}, overrides=wrong))
    state = run_loop(deps)
    assert not state.get("stop") or state["stop"]["stage"] != "subset_exp"
    assert state["best"] == "C1: shared knots"  # the table says so, and a judge that disagrees cannot change it
    records = [g for g in gates(deps) if g["question"]["id"] in ("loop.beats_baseline", "loop.best_method")]
    assert records and all(g["verdict"]["backend"] == "rule" and "judge_verdict" in g for g in records)


# ── RSH-F-03: no self-grading, shadow labels, gate log ──────────────────────────────────────────────


def test_RSH_F_03_every_gate_comes_from_a_component_other_than_the_producer(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    state = run_loop(deps)
    for raw in state["stage_results"]:
        sr = StageResult.model_validate(raw)
        assert sr.gate.judge_id != sr.producer_id and sr.gate.producer_id == sr.producer_id
    producers = {g["verdict"]["producer_id"] for g in gates(deps)}
    assert producers == {"p3.baseline", "p3.ideate", "p3.subset_exp", "p3.write_up"}
    assert {g["verdict"]["judge_id"] for g in gates(deps)} == {"p2.judge", "loop.rule_gate"}


def test_RSH_F_03_self_grading_is_caught_at_each_stage_gate(tmp_path: Path) -> None:
    from vera.loop.stages import ask_gate  # noqa: PLC0415

    for stage in ("baseline", "ideate", "subset_exp", "write_up"):
        deps = make_deps(tmp_path / stage, judge=FakeJudge(judge_id=f"p3.{stage}"))
        q = questions.idea_worth_run("C1: x", "d", "t")[0]
        with pytest.raises(SelfGradingError):
            ask_gate(deps, stage, q, "material", None, {})


def test_RSH_F_03_shadow_answers_are_recorded_beside_every_computable_verdict(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    run_loop(deps)
    records = gates(deps)
    by_q = {}
    for r in records:
        by_q.setdefault(r["question"]["id"], []).append(r)
    assert set(by_q) == {"loop.baseline_reproduced", "loop.idea_worth_run", "loop.beats_baseline", "loop.best_method",
                         "loop.guidance_met"}  # fmt: skip
    assert all(r["shadow_answer"] is None for r in by_q["loop.idea_worth_run"])  # no computable label for a Score
    for q in ("loop.baseline_reproduced", "loop.beats_baseline", "loop.best_method", "loop.guidance_met"):
        assert all(r["shadow_answer"] == r["verdict"]["answer"] for r in by_q[q])  # a correct fake judge agrees
    assert len(by_q["loop.beats_baseline"]) == 4  # 2 ideas x 2 datasets
    assert all("Results from a research-loop run" in r["material"] for r in by_q["loop.beats_baseline"])


def test_RSH_F_03_shadow_answers_follow_the_rendered_numbers() -> None:
    results = {tables.BASELINE: {"analytical": ds(2.001), "airfoil": ds(2.0)},
               "C1: x": {"analytical": ds(2.0004), "airfoil": ds(1.99)}}  # fmt: skip
    _, _, tie = questions.beats_baseline("C1: x", "analytical", results, ["analytical", "airfoil"], 3)
    _, _, win = questions.beats_baseline("C1: x", "airfoil", results, ["analytical", "airfoil"], 3)
    assert tie is False and win is True  # 2.001 and 2.0004 both render as 2.00: a tie is not a win
    _, _, best = questions.best_method("analytical", results, ["analytical", "airfoil"], 3)
    assert best is None  # tied best has no shadow answer


def test_RSH_F_03_the_baseline_shadow_applies_the_registered_tolerance_and_row_set() -> None:
    tol = TARGET["tolerance"]["absolute_pct_points"]
    assert TARGET["datasets"]["analytical"]["reproduction_metric"] == "residual_mse_pct"  # held-out, as registered
    assert TARGET["datasets"]["airfoil"]["reproduction_metric"] == "residual_in_sample_pct"
    # analytical is compared held-out and airfoil in-sample; the other column's value (9.0 here) must not matter
    ok = {tables.BASELINE: {"analytical": ds(2.0 + tol, in_sample=9.0), "airfoil": ds(9.0, in_sample=2.0 - tol)}}
    off = {tables.BASELINE: {"analytical": ds(2.0 + tol + 0.1, in_sample=2.0), "airfoil": ds(9.0, in_sample=2.0)}}
    wrong_basis = {tables.BASELINE: {"analytical": ds(9.0, in_sample=2.0), "airfoil": ds(2.0, in_sample=9.0)}}
    missing = {tables.BASELINE: {"analytical": ds(2.0), "airfoil": ds(0, valid=False, reason="x")}}
    assert questions.baseline_reproduced(TARGET, ok, 3)[2] is True  # exactly at the tolerance matches
    assert questions.baseline_reproduced(TARGET, off, 3)[2] is False
    assert questions.baseline_reproduced(TARGET, wrong_basis, 3)[2] is False  # right numbers in the wrong column
    assert questions.baseline_reproduced(TARGET, missing, 3)[2] is False  # a dataset with no valid result
    _, material, _ = questions.baseline_reproduced(TARGET, ok, 3)
    assert "Analytical 2.0 (compare the held-out column)" in material
    assert "Airfoil 2.0 (compare the in-sample column)" in material  # the judge is told which column to use


def test_RSH_F_03_the_measured_baseline_passes_the_gate_as_registered() -> None:
    """The full-protocol baseline (docs/results/treehfd_baseline_first_runs.md) against the registered target."""
    measured = {tables.BASELINE: {"analytical": ds(2.79, in_sample=0.57), "airfoil": ds(4.73, in_sample=1.52)}}
    assert questions.baseline_reproduced(TARGET, measured, 3)[2] is True


# ── budget and resume across the real graph ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("max_usd", [0.005, 0.012, 0.025, 0.03])
def test_RSH_P_01_the_loop_never_exceeds_its_budget_and_reports_why(tmp_path: Path, max_usd: float) -> None:
    spec = make_spec(max_usd=max_usd)
    deps = make_deps(tmp_path, spec=spec)
    state = run_loop(deps)
    assert state["stop"]["reason"].startswith("budget:")
    assert deps.budget.spent_usd <= max_usd + 1e-9 and deps.ledger.total_cost() <= max_usd + 1e-9
    report = json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))
    assert report["stop_reason"].startswith("budget:") and report["budget"]["max_usd"] == max_usd


def test_RSH_P_01_sandbox_time_counts_against_the_wall_budget(tmp_path: Path) -> None:
    spec = make_spec(max_wall=5)
    deps = make_deps(tmp_path, spec=spec, sandbox=FakeSandbox(seconds=3))  # each experiment charges 3 s
    state = run_loop(deps)
    assert state["stop"]["reason"].startswith("budget: wall")
    assert deps.budget.elapsed_seconds <= 5


def worker(tmp_path: Path, mode: str, crash_at: int | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(WORKER), str(tmp_path), mode] + ([str(crash_at)] if crash_at else [])
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, check=False)


def ledger_components(tmp_path: Path) -> list[str]:
    path = tmp_path / "run_kill-run.jsonl"
    return [json.loads(ln)["component"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_FND_F_02_the_loop_graph_resumes_without_repeating_billed_work(tmp_path: Path) -> None:
    killed = worker(tmp_path, "start", crash_at=2)  # dies at the second implementation call, inside subset_exp
    assert killed.returncode == 3, killed.stderr
    before = ledger_components(tmp_path)
    assert before.count("p3.ideate") == 1 and before.count("p3.subset_exp") == 1  # 2nd call died on entry
    resumed = worker(tmp_path, "resume")
    assert resumed.returncode == 0, resumed.stderr
    after = ledger_components(tmp_path)
    assert after.count("p3.ideate") == 1  # ideation was not repeated
    assert after.count("p3.subset_exp") == 3  # the interrupted node reruns whole: its 1st call again, then the 2nd
    assert "best=C1: shared knots" in resumed.stdout
    assert after.count("p2.judge") == 1 + 4 + 6 + 1  # gates: baseline, 4 scores, 4 beats + 2 best, guidance
    assert after.count("p3.write_up") == 1


def test_FND_F_02_a_resumed_run_restores_what_was_already_spent(tmp_path: Path) -> None:
    worker(tmp_path, "start", crash_at=2)
    spent_in_ledger = sum(
        json.loads(ln)["cost_usd"]
        for ln in (tmp_path / "run_kill-run.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    )
    resumed = worker(tmp_path, "resume")
    assert resumed.returncode == 0, resumed.stderr
    final = json.loads((tmp_path / "run" / "best_so_far.json").read_text(encoding="utf-8"))
    assert final["budget"]["spent_usd"] >= spent_in_ledger - 1e-9  # restored, not reset to zero
    all_cost = sum(
        json.loads(ln)["cost_usd"]
        for ln in (tmp_path / "run_kill-run.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    )
    assert final["budget"]["spent_usd"] == pytest.approx(all_cost)


def test_the_graph_is_a_langgraph_with_sync_checkpoints(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    graph = build_graph(deps, checkpointer=sqlite_checkpointer(tmp_path / "ck.sqlite"))
    run(graph, {"trail": []}, "t")
    state = graph.get_state(run_config("t"))
    assert not state.next and state.values["trail"][-1] == "audit"


# ── the results gate asks only questions that have an answer ───────────────────────────────────────────


def test_RSH_F_02_no_best_method_question_when_no_idea_beat_the_baseline(tmp_path: Path) -> None:
    """The first full live run spent 6000 reasoning tokens on 'which is best?' for a tie, then failed closed."""
    ideas = {"C1": {"analytical": ds(2.4, in_sample=0.6), "airfoil": ds(4.7, in_sample=1.6)},  # identical to baseline
             "C2": {"analytical": ds(2.9), "airfoil": ds(2.6)}}  # fmt: skip
    deps = make_deps(tmp_path, sandbox=FakeSandbox(ideas=ideas))
    state = run_loop(deps)
    assert state.get("stop") is None and state["best"] is None
    assert "loop.best_method" not in deps.judge.asked  # nothing to rank
    assert all(g["question"]["id"] != "loop.best_method" for g in gates(deps))
    decisions = {s["stage"]: s["decision"] for s in state["stage_results"]}
    assert decisions["subset_exp"] == "reject" and decisions["write_up"] == "accept"


def test_RSH_F_02_a_tie_for_best_is_not_put_to_the_judge(tmp_path: Path) -> None:
    same = {"analytical": ds(1.8), "airfoil": ds(2.2)}  # both ideas beat the baseline, with identical numbers
    deps = make_deps(tmp_path, sandbox=FakeSandbox(ideas={"C1": same, "C2": same}))
    state = run_loop(deps)
    assert state.get("stop") is None
    assert "loop.best_method" not in deps.judge.asked  # tied on every dataset: no unique answer to ask for
    assert state["best"] == "C1: shared knots"  # equal wins: the first contender
    check = json.loads((deps.run_dir / "artifacts" / "results_gate.json").read_text(encoding="utf-8"))
    assert check["best_method_tied_not_asked"] == ["analytical", "airfoil"]


# ── per-stage generators and starting from a recorded baseline (the generator comparison) ─────────────


def test_RSH_F_02_stages_can_use_different_generators_through_one_ledger(tmp_path: Path) -> None:
    from vera.loop.generators import ByStage  # noqa: PLC0415

    ledger = Ledger(tmp_path / "run_split.jsonl", run_id="split")
    budget = make_spec().budget.model_copy()
    cheap, strong = FakeGenerator(ledger, budget, cost=0.001), FakeGenerator(ledger, budget, cost=0.02)
    cheap.drafts = strong.drafts = [paper()]
    deps = make_deps(tmp_path, generator=ByStage({"write_up": strong}, default=cheap), ledger=ledger, budget=budget)
    state = run_loop(deps)
    assert state.get("stop") is None
    assert strong.calls == ["p3.write_up"]  # only the write-up went to the strong model
    assert set(cheap.calls) == {"p3.ideate", "p3.subset_exp", "p3.ablation"}
    assert deps.budget.spent_usd == pytest.approx(ledger.total_cost())  # one ledger, one budget
    with pytest.raises(KeyError):
        ByStage({}).generate("s", "p", component="p3.ideate")


def test_RSH_F_02_a_run_can_start_at_the_ideas_stage_from_a_recorded_baseline(tmp_path: Path) -> None:
    from vera.loop.graph import build_graph  # noqa: PLC0415

    first = make_deps(tmp_path / "a")
    recorded = run_loop(first)  # a full run supplies the baseline state
    sandbox = FakeSandbox()
    second = make_deps(tmp_path / "b", sandbox=sandbox)
    initial = {k: recorded[k] for k in ("baseline", "verdicts", "stage_results", "trail", "artifacts")}
    initial = {**initial, "verdicts": {"baseline": recorded["verdicts"]["baseline"]},
               "stage_results": recorded["stage_results"][:1], "trail": ["baseline", "baseline_gate"],
               "artifacts": {"baseline": recorded["artifacts"]["baseline"]}}  # fmt: skip
    state = run_loop(second, start_at="ideate", initial_state=initial)
    assert state.get("stop") is None
    assert state["trail"][:3] == ["baseline", "baseline_gate", "ideate"] and state["trail"][-1] == "audit"
    assert sandbox.calls.count("baseline") == 0  # the recorded baseline was not re-run
    assert build_graph(second, start_at="screen") is not None
