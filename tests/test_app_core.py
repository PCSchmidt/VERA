# ruff: noqa: E501
"""The app core (APP-F-01, APP-C-02): the session key, the Stop button, and the run manager over a fake launcher."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitGenerator, LitJudge, make_lit_spec
from tests.test_retrieval import RETRIEVAL_NODES, FakeRetriever
from vera.app import pipeline
from vera.app import state as app_state
from vera.app.appbudget import STOP_FILE, AppBudget
from vera.app.keystore import InvalidKey, SessionKey
from vera.app.runs import RunError, RunManager
from vera.app.worker import finish_state
from vera.ledger import Ledger
from vera.literature import scoping
from vera.literature.deps import LitDeps
from vera.schemas import BudgetExceeded, RunRequest

KEY = "sk-or-v1-unit-test-marker-0123456789abcdef"
REQUEST = RunRequest(run_id="my-first-run", topic="How do tree ensembles behave under correlated features?",
                     max_usd=1.0, max_wall_seconds=3600)  # fmt: skip


# ── the session key ───────────────────────────────────────────────────────────────────────────────


def test_APP_C_02_the_session_key_is_held_in_memory_and_never_shown() -> None:
    k = SessionKey()
    assert not k.present and k.get() is None
    k.set(f"  {KEY}\n")
    assert k.present and k.get() == KEY
    assert KEY not in repr(k) and KEY not in str(k)
    k.clear()
    assert not k.present and k.get() is None


@pytest.mark.parametrize("bad", ["", "   ", "short", "has a space inside the key text that is long enough", "x" * 301])
def test_a_malformed_key_is_refused_without_echoing_it(bad: str) -> None:
    with pytest.raises(InvalidKey) as err:
        SessionKey().set(bad)
    assert bad.strip() == "" or bad not in str(err.value)


# ── the Stop button ───────────────────────────────────────────────────────────────────────────────


def test_a_stop_file_makes_the_next_charge_raise_and_survives_a_copy(tmp_path: Path) -> None:
    budget = AppBudget(max_usd=1.0, max_wall_seconds=60).watch(tmp_path)
    budget.charge(0.1)
    (tmp_path / STOP_FILE).write_text("stop", encoding="utf-8")
    for b in (budget, budget.model_copy()):
        with pytest.raises(BudgetExceeded, match="stopped by the user"):
            b.charge(0.1)
    assert budget.spent_usd == pytest.approx(0.1)  # nothing is charged for a call that is not made


def test_finish_state_words() -> None:
    assert finish_state({}, "continue") == ("complete", None)
    assert finish_state({"stop": {"stage": "scope", "reason": "awaiting confirmation: x"}}, "start")[0] == (
        "awaiting_confirmation"
    )
    assert (
        finish_state({"stop": {"stage": "read", "reason": "budget: stopped by the user"}}, "continue")[0] == "stopped"
    )
    assert finish_state({"stop": {"stage": "read", "reason": "budget: usd 1.1 > 1.0"}}, "continue")[0] == "stopped"
    assert (
        finish_state(
            {"stop": {"stage": "scope", "reason": "the model's reply had no usable scoped question"}}, "start"
        )[0]
        == "failed"
    )


# ── the run manager over a fake launcher ──────────────────────────────────────────────────────────


class Launches:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, run_id: str, phase: str, env: dict) -> None:
        self.calls.append((run_id, phase, env))


@pytest.fixture
def manager(tmp_path: Path, monkeypatch) -> tuple[RunManager, Launches, SessionKey]:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)  # no .env there
    session, launches = SessionKey(), Launches()
    return RunManager(tmp_path, session, launches), launches, session


def test_APP_F_01_a_run_starts_with_the_key_in_the_workers_environment_only(manager, tmp_path: Path) -> None:
    mgr, launches, session = manager
    session.set(KEY)
    status = mgr.create(REQUEST)
    assert status.state == "queued" and status.max_usd == 1.0 and status.spent_usd == 0.0
    run_id, phase, env = launches.calls[0]
    assert (run_id, phase, env["OPENROUTER_API_KEY"]) == ("my-first-run", "start", KEY)
    written = " ".join(p.read_text(encoding="utf-8") for p in (tmp_path / "runs").rglob("*") if p.is_file())
    assert KEY not in written and "OPENROUTER" not in written  # the key is in no file the app wrote
    assert json.loads(status.model_dump_json()).keys().isdisjoint({"api_key", "key"})


def test_a_run_needs_a_key_and_a_new_name(manager, tmp_path: Path) -> None:
    mgr, launches, session = manager
    with pytest.raises(RunError, match="Connect your OpenRouter key"):
        mgr.create(REQUEST)
    assert not (tmp_path / "runs").exists() and not launches.calls  # refused before anything was created
    session.set(KEY)
    mgr.create(REQUEST)
    with pytest.raises(RunError, match="already exists"):
        mgr.create(REQUEST)


def test_the_status_is_read_from_the_runs_own_files(manager, tmp_path: Path) -> None:
    mgr, _, session = manager
    session.set(KEY)
    mgr.create(REQUEST)
    ledger = Ledger.for_run("my-first-run", root=tmp_path / "data" / "ledger")
    (tmp_path / "data" / "ledger").mkdir(parents=True, exist_ok=True)
    rec = {"cost_usd": 0.0123}
    ledger.path.write_text(json.dumps(rec) + "\n" + json.dumps(rec) + "\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "my-first-run"
    (run_dir / "gates.jsonl").write_text(
        json.dumps({"question": {"id": "lit.relevant"}, "verdict": {"answer": True, "confidence": 0.9, "backend": "glm"}})
        + "\n", encoding="utf-8")  # fmt: skip
    (run_dir / "audit.json").write_text(json.dumps({"summary": "amber"}), encoding="utf-8")
    app_state.write(run_dir, "running", None)
    st = mgr.status("my-first-run")
    assert st.state == "running" and st.spent_usd == pytest.approx(0.0246) and st.audit == "amber"
    assert st.last_verdict == {"question": "lit.relevant", "answer": True, "confidence": 0.9, "backend": "glm"}


def test_confirm_stop_and_resume_only_when_they_make_sense(manager, tmp_path: Path) -> None:
    mgr, launches, session = manager
    session.set(KEY)
    mgr.create(REQUEST)
    run_dir = tmp_path / "runs" / "my-first-run"
    with pytest.raises(RunError, match="not waiting"):
        mgr.confirm("my-first-run", None)
    with pytest.raises(RunError, match="Only a stopped run"):
        mgr.resume("my-first-run")
    app_state.write(run_dir, "running", None)
    assert mgr.stop("my-first-run").state == "stopping" and (run_dir / STOP_FILE).exists()
    app_state.write(run_dir, "stopped", "x")
    with pytest.raises(RunError, match="not running"):
        mgr.stop("my-first-run")
    assert mgr.resume("my-first-run").state == "queued" and launches.calls[-1][1] == "resume"


def test_a_run_id_that_escapes_the_runs_folder_is_refused(manager) -> None:
    mgr, _, _ = manager
    for bad in ("../x", "..", "a/b", "A_B", ""):
        with pytest.raises(RunError):
            mgr.run_dir(bad)


# ── the pipeline: stop at a safe point, resume, nothing repeated ──────────────────────────────────


def make_app_deps(tmp_path: Path) -> LitDeps:
    spec = make_lit_spec("app-run")
    run_dir = tmp_path / "run"
    budget = AppBudget(**spec.budget.model_dump()).watch(run_dir)
    ledger = Ledger(tmp_path / "run_app-run.jsonl", run_id="app-run")
    queries = '```json\n["tree explainability", "functional decomposition"]\n```'
    deps = LitDeps(spec=spec, generator=LitGenerator(ledger, budget, replies={"p3.retrieve": queries}),
                   judge=LitJudge(ledger, budget), budget=budget, run_dir=run_dir, ledger=ledger)  # fmt: skip
    deps.extra["retriever"] = FakeRetriever()
    return deps


def test_APP_F_01_stop_halts_at_the_next_call_and_resume_finishes_without_repeating_work(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(pipeline, "STAGE_NODES", RETRIEVAL_NODES)
    deps = make_app_deps(tmp_path)
    started = pipeline.run_phase(deps, "start")
    assert started["stop"]["reason"].startswith("awaiting confirmation")
    pipeline.confirm(deps.run_dir, None)
    (deps.run_dir / STOP_FILE).write_text("stop", encoding="utf-8")  # the user pressed Stop
    stopped = pipeline.run_phase(deps, "continue")
    assert "stopped by the user" in stopped["stop"]["reason"]
    assert finish_state(stopped, "continue")[0] == "stopped"
    records_at_stop = len(deps.ledger.records())
    spent_at_stop = deps.budget.spent_usd
    assert scoping.read_scope(deps.run_dir).status == "confirmed"  # the confirmation is kept, not asked again

    done = pipeline.run_phase(deps, "resume")  # clears Stop, runs again from the stage that stopped
    assert not done.get("stop") and done["trail"][-1] == "rescreen"
    assert not (deps.run_dir / STOP_FILE).exists()
    assert len(deps.ledger.records()) > records_at_stop and deps.budget.spent_usd >= spent_at_stop
    assert deps.generator.calls.count("p3.scope") == 1  # scoping was not paid for again
