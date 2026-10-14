# ruff: noqa: E501
"""JDG-F-07: each routed question is answered only by its route, wherever it is asked; AUD-F-13: an audit "no" on a
confirmed question stands only if the reference agrees. Fake backends, no network."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from tests.lit_fakes import LitJudge
from tests.test_paper_evidence import make_review
from tests.test_paper_pipeline import finish_review, make_deps, script
from vera.app import pipeline
from vera.judge import cheap_path as cp
from vera.schemas import PaperRequest, Question, QuestionType, Verdict

_ids = itertools.count()


class Fake:
    """A judge backend that answers `answer` with `confidence`, and records what it was asked."""

    def __init__(self, name: str, answer: bool = True, confidence: float = 0.9) -> None:
        self.name, self.cost_rank, self.answer, self.confidence, self.asked = name, 1, answer, confidence, []

    def ask(self, state: str, questions: list[Question], threshold: float | None = None) -> list[Verdict]:
        self.asked += [q.id for q in questions]
        return [Verdict(question_id=q.id, answer=self.answer, confidence=self.confidence, confidence_source="self_report",
                        backend=self.name, escalated=False, cost_usd=0.0, latency_ms=1, trace_id=f"{self.name}-{next(_ids)}",
                        judge_id="p2.judge") for q in questions]  # fmt: skip


def q(qid: str) -> Question:
    return Question(id=qid, type=QuestionType.BOOLEAN, text="?")


def test_JDG_F_07_a_routed_question_reaches_only_its_route(monkeypatch) -> None:
    monkeypatch.setitem(cp.QUESTION_ROUTES, "claim.within_quote", ("glm-flash",))  # a route without Jev
    jev, glm = Fake("jev"), Fake("glm-flash")
    path = cp.cheap_path(ledger=None, budget=None, backends=(jev, glm))
    path.ask("s", [q("claim.within_quote")])
    assert jev.asked == [] and glm.asked == ["claim.within_quote"]
    path.ask("s", [q("sentence.no_fact")])  # routed to Jev then GLM: Jev answers confidently
    assert jev.asked == ["sentence.no_fact"]


def test_JDG_F_07_unrouted_questions_keep_todays_routing() -> None:
    jev, glm = Fake("jev"), Fake("glm-flash")
    path = cp.cheap_path(ledger=None, budget=None, backends=(jev, glm))
    out = path.ask("s", [q("lit.claim_supported"), q("cite.contains_entry")])
    assert [v.backend for v in out] == ["glm-flash", "jev"]  # literature-stage questions to GLM; the rest Jev first
    assert set(cp.QUESTION_ROUTES) == {"claim.within_quote", "sentence.no_fact", "paper.inference_follows"}


def test_JDG_F_07_the_route_is_recorded_on_each_verdict_and_escalates_below_threshold() -> None:
    jev, glm = Fake("jev", confidence=0.5), Fake("glm-flash")
    path = cp.cheap_path(ledger=None, budget=None, backends=(jev, glm))
    (v,) = path.ask("s", [q("paper.inference_follows")])
    assert v.backend == "glm-flash" and jev.asked == ["paper.inference_follows"]  # Jev unsure: GLM answered


def audited(tmp_path: Path, monkeypatch, judge, reference) -> dict:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    light = pipeline.run_paper_audit(deps, judge=judge, reference=reference)
    report = json.loads((deps.run_dir / "paper" / "audit_report.json").read_text("utf-8"))
    return {"light": light, "findings": report["findings"]}


class SaysNo(LitJudge):
    def ask(self, state, questions):
        return [v.model_copy(update={"answer": False, "trace_id": f"audit-{next(_ids)}"}) if v.question_id == "claim.within_quote" else v
                for v in super().ask(state, questions)]  # fmt: skip


def test_AUD_F_13_a_no_the_reference_does_not_confirm_is_a_disagreement(tmp_path: Path, monkeypatch) -> None:
    reference = Fake("sonnet-ref", answer=True)
    out = audited(tmp_path, monkeypatch, SaysNo(), reference)
    within = [f for f in out["findings"] if "says more than its quote" in f["summary"]]
    assert within and all(f["severity"] == "warn" and "the reference judge says yes" in f["summary"] for f in within)
    assert set(reference.asked) == {"claim.within_quote"} and out["light"] == "amber"


def test_AUD_F_13_a_no_the_reference_confirms_fails_even_after_a_write_time_yes(tmp_path: Path, monkeypatch) -> None:
    reference = Fake("sonnet-ref", answer=False)
    out = audited(tmp_path, monkeypatch, SaysNo(), reference)
    within = [f for f in out["findings"] if "says more than its quote" in f["summary"]]
    assert within and all(f["severity"] == "fail" for f in within)
    assert all(f["verdicts"][-1]["backend"] == "sonnet-ref" for f in within) and out["light"] == "red"
