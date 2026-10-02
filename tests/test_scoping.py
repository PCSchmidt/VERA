"""RSH-F-08: topic scoping, the confirmation pause and the user's record. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import SCOPED_REPLY, LitJudge, fenced, make_lit_deps, make_lit_spec
from vera.graph import resume, run_config
from vera.judge.cheap_path import CheapPath
from vera.judge.router import Router
from vera.literature import questions, scoping
from vera.literature.graph import AWAITING, _graph, continue_topic_run, start_topic_run
from vera.schemas import RoutingPolicy, ScopedQuestion, SelfGradingError, StageResult, Verdict


def best(deps) -> dict:
    return json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))


def test_RSH_F_08_a_topic_yields_a_scoped_question_and_the_run_waits(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    state = start_topic_run(deps)
    scoped = scoping.read_scope(deps.run_dir)
    assert scoped is not None and scoped.status == "proposed" and scoped.confirmed_by is None
    assert scoped.question == SCOPED_REPLY["question"] and scoped.empirical and scoped.candidate_parent == "2510.24815"
    assert scoped.why_researchable
    assert state["stop"]["reason"] == AWAITING and state["trail"] == ["scope", "scope_gate"]
    assert best(deps)["stop_reason"] == AWAITING and best(deps)["stage_reached"] == "scope"
    # exactly the scoping calls were made: one generation and one verdict
    assert deps.generator.calls == ["p3.scope"] and deps.judge.asked == ["lit.question_scoped"]
    assert [r.component for r in deps.ledger.records()] == ["p3.scope", "p2.judge"]
    (sr,) = [StageResult.model_validate(s) for s in state["stage_results"]]
    assert (sr.stage, sr.decision) == ("scope", "accept") and sr.gate.judge_id != sr.producer_id


def test_RSH_F_08_continuing_does_not_repeat_the_scoping_calls(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    start_topic_run(deps)
    scoping.confirm_scope(deps.run_dir, "Chris")
    state = continue_topic_run(deps)
    assert deps.generator.calls == ["p3.scope"] and deps.judge.asked == ["lit.question_scoped"]  # not repeated
    assert len(deps.ledger.records()) == 2
    assert state["trail"] == ["scope", "scope_gate", "confirm"] and not state.get("stop")
    assert best(deps)["stop_reason"] == "completed"


def test_RSH_F_08_nothing_after_scoping_runs_without_a_confirmation(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    ran: list[str] = []
    extra = [("later", "retrieve", lambda d: lambda state: ran.append("later") or {"trail": ["later"]})]
    start_topic_run(deps, extra_nodes=extra)
    with pytest.raises(scoping.ScopeNotConfirmedError):
        continue_topic_run(deps, extra_nodes=extra)
    # resumed some other way, bypassing continue_topic_run: the confirm node still stops the run
    graph = _graph(deps, extra)
    state = resume(graph, deps.spec.run_id)
    assert state["stop"]["stage"] == "scope" and "awaiting confirmation" in state["stop"]["reason"] and ran == []
    assert "later" not in graph.get_state(run_config(deps.spec.run_id)).values["trail"]


def test_RSH_F_08_stages_after_scoping_run_once_confirmed(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    ran: list[str] = []
    extra = [("later", "retrieve", lambda d: lambda state: ran.append("later") or {"trail": ["later"]})]
    start_topic_run(deps, extra_nodes=extra)
    scoping.confirm_scope(deps.run_dir, "Chris")
    state = continue_topic_run(deps, extra_nodes=extra)
    assert ran == ["later"] and state["trail"][-1] == "later"


def test_RSH_F_08_an_edit_replaces_the_question_and_is_recorded(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    start_topic_run(deps)
    confirmed = scoping.confirm_scope(deps.run_dir, "Chris", question="Does TreeHFD stay accurate under correlation?")
    assert confirmed.status == "edited" and confirmed.confirmed_by == "Chris" and confirmed.confirmed_at.endswith("Z")
    assert scoping.read_scope(deps.run_dir).question == "Does TreeHFD stay accurate under correlation?"
    again = scoping.confirm_scope(deps.run_dir, "Chris")  # plain confirmation of the (edited) question
    assert again.status == "confirmed" and again.question == confirmed.question


def test_RSH_F_08_a_confirmation_with_no_identity_is_rejected(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    start_topic_run(deps)
    for who in ("", "   "):
        with pytest.raises(ValueError):
            scoping.confirm_scope(deps.run_dir, who)
    assert scoping.read_scope(deps.run_dir).status == "proposed"
    with pytest.raises(FileNotFoundError):
        scoping.confirm_scope(tmp_path / "nowhere", "Chris")


def test_RSH_F_08_the_scoping_stage_cannot_grade_itself(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    deps.judge = LitJudge(deps.ledger, deps.budget, judge_id="p3.scope")
    with pytest.raises(SelfGradingError):
        start_topic_run(deps)


def test_RSH_F_08_scoping_stays_inside_its_own_cap(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path, cost=0.30)  # one generation costs more than the $0.25 scoping cap
    state = start_topic_run(deps)
    assert state["stop"]["reason"].startswith("budget")
    assert deps.budget.spent_usd <= deps.scope_cap_usd  # refused before the call crossed the cap
    assert deps.budget.max_usd == 2.0  # the run's own budget is restored for after the confirmation


def test_RSH_F_08_a_question_the_judge_rejects_stops_the_run(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    deps.judge = LitJudge(deps.ledger, deps.budget, answers={"lit.question_scoped": False})
    state = start_topic_run(deps)
    assert state["stop"]["reason"].startswith("gate: the scoped question was rejected")
    sr = StageResult.model_validate(state["stage_results"][-1])
    assert sr.decision == "reject" and sr.deciding_gates == [0]
    assert scoping.read_scope(deps.run_dir).status == "proposed"


def test_RSH_F_08_an_unsure_judge_fails_closed(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path)
    deps.judge = LitJudge(deps.ledger, deps.budget, confidence=0.3)
    state = start_topic_run(deps)
    assert "not confident" in state["stop"]["reason"]


def test_RSH_F_08_a_reply_with_no_question_is_retried_then_stops(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path, replies={"p3.scope": ["I cannot decide."]})
    state = start_topic_run(deps)
    assert deps.generator.calls == ["p3.scope", "p3.scope"] and "no usable" in state["stop"]["reason"]
    blank = fenced({"question": " ", "why_researchable": "x", "empirical": False})
    deps2 = make_lit_deps(tmp_path / "b", replies={"p3.scope": [blank, fenced(SCOPED_REPLY)]})
    assert start_topic_run(deps2)["stop"]["reason"] == AWAITING  # the second reply was usable


def test_RSH_F_08_a_non_empirical_proposal_carries_no_parent(tmp_path: Path) -> None:
    reply = {"question": "What do LLM judges get wrong about numbers?", "why_researchable": "a literature exists",
             "empirical": False, "candidate_parent": "2510.24815", "no_parent_reason": "no experiments needed"}
    deps = make_lit_deps(tmp_path, replies={"p3.scope": fenced(reply)})
    start_topic_run(deps)
    scoped = scoping.read_scope(deps.run_dir)
    assert isinstance(scoped, ScopedQuestion) and not scoped.empirical and scoped.candidate_parent is None


class Backend:
    def __init__(self, name: str) -> None:
        self.name, self.cost_rank, self.seen = name, 1, []

    def ask(self, state, qs, **kw):
        self.seen += [q.id for q in qs]
        return [Verdict(question_id=q.id, answer=True, confidence=0.99, confidence_source="self_report",
                        backend=self.name, escalated=False, cost_usd=0, latency_ms=1, trace_id="t",
                        judge_id="p2.router") for q in qs]  # fmt: skip


def test_RSH_F_08_a_lit_question_reaches_glm_not_jev() -> None:
    jev, glm = Backend("jev"), Backend("glm")
    path = CheapPath(Router([jev, glm], RoutingPolicy()), Router([glm], RoutingPolicy()))
    scoped = ScopedQuestion(topic_id="t", question="q?", why_researchable="w", empirical=False)
    q, material = questions.question_scoped("t", scoped)
    path.ask(material, [q])
    assert glm.seen == ["lit.question_scoped"] and jev.seen == []


def test_RSH_F_08_the_users_note_reaches_the_prompt_and_the_key_papers_never_do(tmp_path: Path) -> None:
    from tests.lit_fakes import TOPIC  # noqa: PLC0415

    topic = TOPIC.model_copy(update={"scope_hint": "Non-empirical. A good question is about the evidence.",
                                     "key_papers_ref": "data/topics/t-a.json"})  # fmt: skip
    deps = make_lit_deps(tmp_path, spec=make_lit_spec(topic=topic))
    prompt = scoping.scope_prompt(deps)
    assert "Non-empirical. A good question is about the evidence." in prompt
    assert "key_papers" not in prompt and "data/topics" not in prompt
