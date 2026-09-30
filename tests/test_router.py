"""JDG-F-02 and JDG-F-03: routing order, escalation and threshold precedence, with fake backends. No network."""

from __future__ import annotations

import pytest

from vera.judge.router import Router
from vera.schemas import Question, QuestionType, RoutingPolicy, Verdict

Q1 = Question(id="loop.beats_baseline", type=QuestionType.BOOLEAN, text="Beats baseline?")
Q2 = Question(id="aud.num.consistent", type=QuestionType.BOOLEAN, text="Number consistent?")
Q3 = Question(id="loop.best", type=QuestionType.CHOICE, text="Best?", options=["A", "B"])


class FakeBackend:
    """Returns a fixed confidence per question id (default `confidence`); records what it was asked."""

    def __init__(self, name: str, cost_rank: int, confidence: float = 0.9, per_q: dict | None = None,
                 fail: bool = False) -> None:  # fmt: skip
        self.name, self.cost_rank, self.confidence, self.per_q, self.fail = (
            name,
            cost_rank,
            confidence,
            per_q or {},
            fail,
        )
        self.asked: list[list[str]] = []

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        self.asked.append([q.id for q in questions])
        if self.fail:
            raise ConnectionError("dns failure")
        return [
            Verdict(
                question_id=q.id,
                answer=True if q.type is QuestionType.BOOLEAN else "A",
                confidence=self.per_q.get(q.id, self.confidence),
                confidence_source="self_report",
                backend=self.name,
                escalated=False,
                cost_usd=0.0,
                latency_ms=1,
                trace_id="t",
                judge_id=f"p2.{self.name}",
            )  # fmt: skip
            for q in questions
        ]


def test_JDG_F_02_tries_backends_in_cost_order() -> None:
    cheap, ref = FakeBackend("cheap", 0), FakeBackend("ref", 1)
    verdicts = Router([ref, cheap]).ask("s", [Q1, Q2])
    assert cheap.asked == [["loop.beats_baseline", "aud.num.consistent"]] and ref.asked == []
    assert [v.backend for v in verdicts] == ["cheap", "cheap"] and not any(v.escalated for v in verdicts)


def test_JDG_F_02_escalates_only_low_confidence_questions() -> None:
    cheap = FakeBackend("cheap", 0, per_q={"aud.num.consistent": 0.4})
    ref = FakeBackend("ref", 1)
    verdicts = Router([cheap, ref], RoutingPolicy(default_threshold=0.7)).ask("s", [Q1, Q2])
    assert ref.asked == [["aud.num.consistent"]]
    assert [(v.backend, v.escalated) for v in verdicts] == [("cheap", False), ("ref", True)]


def test_JDG_F_02_at_threshold_does_not_escalate() -> None:
    cheap, ref = FakeBackend("cheap", 0, confidence=0.7), FakeBackend("ref", 1)
    Router([cheap, ref], RoutingPolicy(default_threshold=0.7)).ask("s", [Q1])
    assert ref.asked == []


def test_JDG_F_02_escalation_cap() -> None:
    a, b, c = FakeBackend("a", 0, 0.1), FakeBackend("b", 1, 0.1), FakeBackend("c", 2)
    verdicts = Router([a, b, c], RoutingPolicy(max_escalations=1)).ask("s", [Q1])
    assert c.asked == [] and verdicts[0].backend == "b" and verdicts[0].escalated
    assert Router([a, b, c], RoutingPolicy(max_escalations=0)).ask("s", [Q1])[0].backend == "a"


def test_JDG_F_02_failed_backend_escalates_and_last_failure_keeps_earlier_verdict() -> None:
    cheap_down, ref = FakeBackend("cheap", 0, fail=True), FakeBackend("ref", 1)
    assert Router([cheap_down, ref]).ask("s", [Q1])[0].backend == "ref"
    cheap_low, ref_down = FakeBackend("cheap", 0, 0.2), FakeBackend("ref", 1, fail=True)
    (v,) = Router([cheap_low, ref_down]).ask("s", [Q1])
    assert (v.backend, v.confidence, v.escalated) == ("cheap", 0.2, False)
    with pytest.raises(ConnectionError):
        Router([FakeBackend("only", 0, fail=True)]).ask("s", [Q1])


@pytest.mark.parametrize(
    ("policy", "override", "escalates"),
    [
        (RoutingPolicy(default_threshold=0.5), None, False),  # 0.6 >= default 0.5
        (RoutingPolicy(default_threshold=0.5, per_type={QuestionType.BOOLEAN: 0.8}), None, True),  # type beats default
        (RoutingPolicy(per_type={QuestionType.BOOLEAN: 0.8}, per_question={"loop.beats_baseline": 0.5}), None, False),
        (RoutingPolicy(per_question={"loop.beats_baseline": 0.5}), 0.9, True),  # call beats question id
    ],
)
def test_JDG_F_03_threshold_precedence(policy: RoutingPolicy, override: float | None, escalates: bool) -> None:
    cheap, ref = FakeBackend("cheap", 0, confidence=0.6), FakeBackend("ref", 1)
    Router([cheap, ref], policy).ask("s", [Q1], threshold=override)
    assert (ref.asked != []) is escalates


def test_JDG_F_03_per_type_threshold_applies_only_to_that_type() -> None:
    cheap, ref = FakeBackend("cheap", 0, confidence=0.6), FakeBackend("ref", 1)
    policy = RoutingPolicy(default_threshold=0.5, per_type={QuestionType.CHOICE: 0.8})
    Router([cheap, ref], policy).ask("s", [Q1, Q3])
    assert ref.asked == [["loop.best"]]
