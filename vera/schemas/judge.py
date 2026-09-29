"""Judge layer (P2) schemas: docs/03-interfaces.md, "Judge layer"."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

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
    default_threshold: float = 0.7
    per_question: dict[str, float] = {}
    max_escalations: int = 1
