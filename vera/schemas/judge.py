"""Judge layer (P2) schemas: docs/03-interfaces.md, "Judge layer"."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator


class QuestionType(StrEnum):
    CHOICE = "choice"  # pick one of `options`
    SCORE = "score"  # integer on a rubric scale
    BOOLEAN = "boolean"  # true/false with probability


class Question(BaseModel):
    id: str  # stable ID, e.g. "aud.cite.exists"
    type: QuestionType
    text: str  # one atomic question
    options: list[str] | None = None  # CHOICE only
    scale: tuple[int, int] | None = None  # SCORE only, e.g. (1, 5)
    rubric: str | None = None  # SCORE guidance


class SelfGradingError(ValueError):
    """A component tried to issue the verdict on its own artifact."""


class Verdict(BaseModel):
    question_id: str
    answer: bool | int | str
    probabilities: dict[str, float] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    # where confidence came from: "logprobs" = the model's own probabilities (token logprobs or a
    # decision model's native distribution); "self_report" = stated by the model; "none" = malformed
    confidence_source: Literal["logprobs", "self_report", "none"] | None = None
    backend: str  # which backend produced the final answer
    escalated: bool  # True if any cheaper backend was bypassed
    cost_usd: float
    latency_ms: int
    trace_id: str
    producer_id: str | None = None  # component that produced the judged artifact
    judge_id: str  # component issuing this verdict (must != producer_id)

    @model_validator(mode="after")
    def _no_self_grading(self) -> Verdict:
        if self.producer_id is not None and self.judge_id == self.producer_id:
            raise SelfGradingError(
                f"judge_id == producer_id ({self.judge_id!r}): a component may not grade its own work"
            )
        return self


class JudgeBackend(Protocol):
    name: str
    cost_rank: int  # lower = tried first

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]: ...


class RoutingPolicy(BaseModel):
    """Escalation thresholds. Precedence: per-call override > per_question > per_type > default."""

    default_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    per_type: dict[QuestionType, float] = {}  # per question type (JDG-F-03)
    per_question: dict[str, float] = {}  # per question id; overrides per_type
    max_escalations: int = Field(default=1, ge=0)

    def threshold_for(self, question: Question, override: float | None = None) -> float:
        if override is not None:
            return override
        if question.id in self.per_question:
            return self.per_question[question.id]
        return self.per_type.get(question.type, self.default_threshold)


class BenchmarkItem(BaseModel):
    """One labelled judge-benchmark item; the label is known from how the item was built (risk R3)."""

    id: str  # stable, e.g. "cite-0042"
    task: Literal["loop_gate", "numeric", "citation", "claim_support"]
    split: Literal["dev", "test"]  # dev = tuning; test = reporting only (docs/06 §5)
    question: Question
    state: str  # the material the judge sees
    label: bool | int | str  # correct answer
    construction: dict[str, str | int | float | bool]  # kind, source, seed
    generator: str  # generator name and version

    @model_validator(mode="after")
    def _label_answers_question(self) -> BenchmarkItem:
        q, label = self.question, self.label
        if q.type is QuestionType.BOOLEAN:
            valid = isinstance(label, bool)
        elif q.type is QuestionType.CHOICE:
            valid = isinstance(label, str) and label in (q.options or [])
        else:
            lo, hi = q.scale or (1, 5)
            valid = isinstance(label, int) and not isinstance(label, bool) and lo <= label <= hi
        if not valid:
            raise ValueError(f"item {self.id!r}: label {label!r} is not a valid answer to a {q.type} question")
        return self
