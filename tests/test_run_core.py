"""Increment 2 run foundation: RunSpec (RSH-F-01), budget stop (RSH-P-01, RSH-F-06), run ledger, cheap path.

No network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.test_router import FakeBackend
from vera.judge.cheap_path import CheapPath, cheap_path
from vera.judge.router import Router
from vera.ledger import CallResult, Ledger, LedgerExistsError, metered_call
from vera.loop import LOOP_QUESTION_IDS
from vera.loop.stop import guard_stage, route_after, write_best_so_far
from vera.schemas import (
    STAGES,
    Budget,
    LedgerRecord,
    OutputGuidance,
    ProblemSpec,
    Question,
    QuestionType,
    RoutingPolicy,
    RunSpec,
)

COMMIT = "a" * 40


def make_spec(**over) -> RunSpec:
    fields = {
        "run_id": "treehfd-001",
        "problem": ProblemSpec(
            parent_id="2510.24815",
            repo_url="https://github.com/ThalesGroup/treehfd",
            repo_commit=COMMIT,
            metric="decomposition_residual",
            datasets=["adult"],
            subset={"n_samples": 1000, "n_trees": 50},
        ),
        "guidance": OutputGuidance(max_words=2500, required_sections=["abstract", "results"]),
        "budget": Budget(max_usd=3.0, max_wall_seconds=7200),
        "models": {"ideate": "glm-flash", "write_up": "sonnet-ref"},
    }
    return RunSpec(**(fields | over))


# ── RSH-F-01: the run spec ───────────────────────────────────────────────────────────────────────────


def test_RSH_F_01_run_spec_round_trips() -> None:
    spec = make_spec()
    assert RunSpec.model_validate_json(spec.model_dump_json()) == spec


@pytest.mark.parametrize(
    "over",
    [
        {"run_id": "../escape"},
        {"run_id": ""},
        {"run_id": "has space"},
        {"budget": Budget(max_usd=0.0, max_wall_seconds=60)},
        {"budget": Budget(max_usd=3.0, max_wall_seconds=60, spent_usd=0.5)},
        {"models": {"not_a_stage": "glm-flash"}},
    ],
)
def test_RSH_F_01_invalid_run_specs_are_rejected(over: dict) -> None:
    with pytest.raises(ValidationError):
        make_spec(**over)


@pytest.mark.parametrize("commit", ["main", "abc123", "g" * 40, "A" * 40])
def test_RSH_F_01_repo_commit_must_be_pinned(commit: str) -> None:
    with pytest.raises(ValidationError):
        ProblemSpec(parent_id="x", repo_url="u", repo_commit=commit, metric="m", datasets=["d"])


def test_RSH_F_01_datasets_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        ProblemSpec(parent_id="x", repo_url="u", repo_commit=COMMIT, metric="m", datasets=[])


# ── per-run ledger and provider ──────────────────────────────────────────────────────────────────────


def test_run_ledger_is_one_file_per_run_and_never_reused(tmp_path: Path) -> None:
    ledger = Ledger.for_run("r1", root=tmp_path)
    assert ledger.path == tmp_path / "run_r1.jsonl" and ledger.run_id == "r1"
    metered_call(
        lambda: CallResult(text="x", model="m", cost_usd=0.001),
        ledger=ledger, budget=Budget(max_usd=1.0, max_wall_seconds=60), component="t", backend="b", model="m",
        estimate_usd=0.01,
    )  # fmt: skip
    with pytest.raises(LedgerExistsError):
        Ledger.for_run("r1", root=tmp_path)  # a new start over an existing ledger
    assert len(Ledger.for_run("r1", root=tmp_path, resume=True).records()) == 1  # resume appends, keeps the records


def test_ledger_records_the_serving_provider(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "run.jsonl")
    budget = Budget(max_usd=1.0, max_wall_seconds=60)
    kwargs = {"ledger": ledger, "budget": budget, "component": "t", "backend": "b", "model": "m", "estimate_usd": 0.01}
    metered_call(lambda: CallResult(text="x", model="m", provider="DeepInfra"), **kwargs)
    metered_call(lambda: CallResult(text="x", model="m"), **kwargs)
    with pytest.raises(RuntimeError):
        metered_call(lambda: (_ for _ in ()).throw(RuntimeError("down")), **kwargs)
    assert [r.provider for r in ledger.records()] == ["DeepInfra", None, None]
    old = {k: v for k, v in json.loads(ledger.path.read_text().splitlines()[0]).items() if k != "provider"}
    assert LedgerRecord.model_validate(old).provider is None  # v0.7 ledgers still load


# ── the cheap path ───────────────────────────────────────────────────────────────────────────────────


def q(id_: str) -> Question:
    return Question(id=id_, type=QuestionType.BOOLEAN, text="?")


def test_loop_questions_go_straight_to_glm_and_the_rest_through_jev() -> None:
    jev, glm = FakeBackend("jev", 1, confidence=0.95), FakeBackend("glm", 2, confidence=0.9)
    path = cheap_path(ledger=None, budget=None, backends=(jev, glm))  # type: ignore[arg-type]
    other = q("aud.cite.exists")
    questions = [q(i) for i in sorted(LOOP_QUESTION_IDS) + ["loop.some_new_question"]] + [other]
    verdicts = path.ask("state", questions)
    assert [v.question_id for v in verdicts] == [x.id for x in questions]  # order kept
    assert sorted(jev.asked[0]) == ["aud.cite.exists"]  # Jev never sees a loop question, whatever it would say
    assert sorted(glm.asked[0]) == sorted([*LOOP_QUESTION_IDS, "loop.some_new_question"])  # by prefix, not by list
    assert {v.backend for v in verdicts if v.question_id in LOOP_QUESTION_IDS} == {"glm"}


def test_other_questions_escalate_from_jev_to_glm_below_the_default_threshold() -> None:
    jev, glm = FakeBackend("jev", 1, confidence=0.5), FakeBackend("glm", 2, confidence=0.9)
    (v,) = cheap_path(ledger=None, budget=None, backends=(jev, glm)).ask("s", [q("aud.cite.exists")])  # type: ignore[arg-type]
    assert (v.backend, v.escalated) == ("glm", True)
    jev2, glm2 = FakeBackend("jev", 1, confidence=0.9), FakeBackend("glm", 2)
    (v2,) = cheap_path(ledger=None, budget=None, backends=(jev2, glm2)).ask("s", [q("aud.cite.exists")])  # type: ignore[arg-type]
    assert (v2.backend, v2.escalated, glm2.asked) == ("jev", False, [])
    assert isinstance(CheapPath(Router([jev], RoutingPolicy()), Router([glm])), CheapPath)


# ── RSH-P-01 and RSH-F-06: the budget stop ──────────────────────────────────────────────────────────


def fake_stage(name: str, ledger: Ledger, budget: Budget, calls: int, cost: float, estimate: float | None = None):
    """A node making `calls` metered calls of `cost` each; the estimate is an upper bound, as the real backends'."""

    def node(state: dict) -> dict:
        for _ in range(calls):
            metered_call(
                lambda: CallResult(text="x", model="fake", cost_usd=cost),
                ledger=ledger, budget=budget, component=f"p3.{name}", backend="fake", model="fake",
                estimate_usd=estimate if estimate is not None else cost,
            )  # fmt: skip
        return {"artifacts": {**(state.get("artifacts") or {}), name: f"artifacts/{name}.json"}}

    return guard_stage(name, node)


def run_stages(spec: RunSpec, ledger: Ledger, budget: Budget, plan: dict[str, tuple[int, float]]) -> dict:
    state: dict = {}
    for stage, (calls, cost) in plan.items():
        state |= fake_stage(stage, ledger, budget, calls, cost)(state)
        if route_after("next", "end")(state) == "end":
            break
    return state


PLAN = {"baseline": (3, 0.4), "ideate": (3, 0.4), "subset_exp": (3, 0.4), "write_up": (3, 0.4)}  # 4.8 > 3.0


@pytest.mark.parametrize("max_usd", [0.3, 1.0, 1.2, 1.9, 2.4, 2.9, 3.0])
def test_RSH_P_01_spend_never_exceeds_the_budget(tmp_path: Path, max_usd: float) -> None:
    """Exhaustion at the first call, inside a stage, and exactly on a stage boundary (1.2 = 3 calls x 0.4)."""
    spec = make_spec(budget=Budget(max_usd=max_usd, max_wall_seconds=7200))
    ledger, budget = Ledger(tmp_path / "run.jsonl"), spec.budget.model_copy()
    state = run_stages(spec, ledger, budget, PLAN)
    assert state["stop"]["reason"].startswith("budget:")
    assert budget.spent_usd <= max_usd + 1e-9
    assert ledger.total_cost() == pytest.approx(budget.spent_usd)  # everything spent is in the ledger


def test_RSH_P_01_wall_clock_and_call_limits_stop_the_run_too(tmp_path: Path) -> None:
    spec = make_spec()
    budget = Budget(max_usd=100.0, max_wall_seconds=7200, max_model_calls=4)
    state = run_stages(spec, Ledger(tmp_path / "r.jsonl"), budget, PLAN)
    assert state["stop"]["stage"] == "ideate" and budget.model_calls_used == 4  # 3 + 1, then the 5th is refused
    walled = Budget(max_usd=100.0, max_wall_seconds=1, elapsed_seconds=2)  # already over the wall limit
    assert "wall" in run_stages(spec, Ledger(tmp_path / "w.jsonl"), walled, PLAN)["stop"]["reason"]


def test_RSH_P_01_a_stopped_run_spends_nothing_more(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run.jsonl"), Budget(max_usd=0.5, max_wall_seconds=7200)
    stopped = {"stop": {"stage": "baseline", "reason": "budget: x"}}
    assert fake_stage("ideate", ledger, budget, 3, 0.1)(stopped) == {}
    assert ledger.records() == [] and budget.spent_usd == 0.0


def test_RSH_F_06_best_so_far_report_names_the_stop_reason_and_stage(tmp_path: Path) -> None:
    spec = make_spec(budget=Budget(max_usd=2.0, max_wall_seconds=7200))
    ledger, budget = Ledger(tmp_path / "run.jsonl"), spec.budget.model_copy()
    state = run_stages(spec, ledger, budget, PLAN)  # baseline 1.2, ideate fails after 2 of 3 calls
    report = write_best_so_far(state, spec, budget, tmp_path / "best_so_far.json")
    on_disk = json.loads((tmp_path / "best_so_far.json").read_text())
    assert on_disk["stop_reason"].startswith("budget: usd") and on_disk["stage_reached"] == "ideate"
    assert report.stages_completed == ["baseline"] and report.artifacts == {"baseline": "artifacts/baseline.json"}
    assert report.budget.spent_usd <= 2.0 and report.run_id == "treehfd-001"


def test_RSH_F_06_a_completed_run_reports_completion(tmp_path: Path) -> None:
    spec = make_spec(budget=Budget(max_usd=10.0, max_wall_seconds=7200))
    state = run_stages(spec, Ledger(tmp_path / "r.jsonl"), spec.budget.model_copy(), PLAN)
    report = write_best_so_far(state, spec, spec.budget, tmp_path / "r.json")
    assert report.stop_reason == "completed" and report.stages_completed == list(PLAN)


def test_guard_stage_rejects_unknown_stages_and_lets_other_errors_through() -> None:
    with pytest.raises(ValueError):
        guard_stage("brainstorm", lambda s: {})

    def boom(state: dict) -> dict:
        raise KeyError("bug")

    with pytest.raises(KeyError):  # only budget exhaustion is a clean stop; bugs stay loud
        guard_stage("baseline", boom)({})
    assert set(STAGES) >= {"baseline", "ideate", "subset_exp", "write_up", "audit"}
