"""Offline fakes for the literature stage: a scripted generator and a judge that says what a test tells it to."""

from __future__ import annotations

import json
from pathlib import Path

from vera.ledger import CallResult, Ledger, metered_call
from vera.literature.deps import LitDeps
from vera.schemas import Budget, OutputGuidance, Question, RunSpec, Topic, Verdict

TOPIC = Topic(id="t-a", text="explainability of tree ensembles under correlated features")
SCOPED_REPLY = {
    "question": "Does a Hoeffding-decomposition explainer stay accurate when features are correlated?",
    "why_researchable": "Small public datasets and public code exist; each run takes minutes on a CPU.",
    "empirical": True,
    "candidate_parent": "2510.24815",
    "no_parent_reason": None,
}


def fenced(data: dict) -> str:
    return "```json\n" + json.dumps(data) + "\n```"


def make_lit_spec(run_id: str = "lit-run", max_usd: float = 2.0, topic: Topic = TOPIC) -> RunSpec:
    return RunSpec(run_id=run_id, topic=topic, guidance=OutputGuidance(max_words=1500),
                   budget=Budget(max_usd=max_usd, max_wall_seconds=7200))  # fmt: skip


class LitGenerator:
    """Replies by component from a script (a string, or a list given in order, the last repeating); every call is
    metered, so the ledger and the budget see it."""

    def __init__(self, ledger: Ledger, budget: Budget, *, cost: float = 0.01, replies: dict | None = None) -> None:
        self.ledger, self.budget, self.cost = ledger, budget, cost
        self.replies = {"p3.scope": fenced(SCOPED_REPLY)} | (replies or {})
        self.calls: list[str] = []

    def generate(self, system: str, prompt: str, *, component: str) -> str:
        self.calls.append(component)
        reply = self.replies[component]
        if isinstance(reply, list):
            reply = reply.pop(0) if len(reply) > 1 else reply[0]
        return metered_call(lambda: CallResult(text=reply, model="fake-gen", cost_usd=self.cost), ledger=self.ledger,
                            budget=self.budget, component=component, backend="fake", model="fake-gen",
                            estimate_usd=self.cost).text  # fmt: skip


class LitJudge:
    """Answers from `answers` by question id (default: true), with a fixed confidence."""

    def __init__(self, ledger: Ledger | None = None, budget: Budget | None = None, *, answers: dict | None = None,
                 confidence: float = 0.9, judge_id: str = "p2.judge") -> None:  # fmt: skip
        self.ledger, self.budget, self.answers, self.confidence = ledger, budget, answers or {}, confidence
        self.judge_id = judge_id
        self.asked: list[str] = []

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        out = []
        for q in questions:
            self.asked.append(q.id)
            if self.ledger is not None and self.budget is not None:
                metered_call(lambda: CallResult(text="x", model="fake-judge", cost_usd=0.0001), ledger=self.ledger,
                             budget=self.budget, component="p2.judge", backend="fake", model="fake-judge",
                             estimate_usd=0.0001)  # fmt: skip
            out.append(Verdict(question_id=q.id, answer=self.answers.get(q.id, True), confidence=self.confidence,
                               confidence_source="self_report", backend="fake", escalated=False, cost_usd=0.0001,
                               latency_ms=1, trace_id="t", judge_id=self.judge_id))  # fmt: skip
        return out


def make_lit_deps(tmp_path: Path, *, spec: RunSpec | None = None, generator=None, judge=None, cost: float = 0.01,
                  replies: dict | None = None, run_id: str = "lit-run") -> LitDeps:  # fmt: skip
    spec = spec or make_lit_spec(run_id)
    budget = spec.budget.model_copy()
    ledger = Ledger(tmp_path / f"run_{run_id}.jsonl", run_id=run_id)
    return LitDeps(
        spec=spec, generator=generator or LitGenerator(ledger, budget, cost=cost, replies=replies),
        judge=judge or LitJudge(ledger, budget), budget=budget, run_dir=tmp_path / "run", ledger=ledger,
    )  # fmt: skip
