"""Research agent (P3) schemas: docs/03-interfaces.md, "Research agent"."""

from __future__ import annotations

import re
from typing import Literal, get_args

from pydantic import BaseModel, field_validator, model_validator

from vera.schemas.foundation import Budget
from vera.schemas.judge import SelfGradingError, Verdict


class StageResult(BaseModel):
    run_id: str
    stage: Literal["baseline", "ideate", "subset_exp", "full_exp", "ablation", "write_up", "audit"]
    artifact_ref: str  # path/ID of produced artifact
    producer_id: str
    gate: Verdict  # issued by a different component
    decision: Literal["accept", "refine", "reject"]
    metrics: dict[str, float] = {}
    budget_after: Budget

    @model_validator(mode="after")
    def _gate_not_self_issued(self) -> StageResult:
        # Verdict's own rule can't see this stage's producer when gate.producer_id is empty.
        if self.gate.judge_id == self.producer_id:
            raise SelfGradingError(f"stage {self.stage!r}: gate issued by its own producer ({self.producer_id!r})")
        if self.gate.producer_id is not None and self.gate.producer_id != self.producer_id:
            raise SelfGradingError(
                f"stage {self.stage!r}: gate judges {self.gate.producer_id!r}'s work, "
                f"but the stage was produced by {self.producer_id!r}"
            )
        return self


STAGES: tuple[str, ...] = get_args(StageResult.model_fields["stage"].annotation)
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_COMMIT = re.compile(r"[0-9a-f]{40}")


class ProblemSpec(BaseModel):
    parent_id: str  # arXiv id or DOI of the parent paper
    repo_url: str  # parent code
    repo_commit: str  # pinned commit, 40 hex characters
    metric: str  # the quality metric the loop optimises
    datasets: list[str]
    subset: dict[str, int | float | str] = {}

    @field_validator("repo_commit")
    @classmethod
    def _commit(cls, v: str) -> str:
        if not _COMMIT.fullmatch(v):
            raise ValueError("repo_commit must be a pinned 40-character hex commit")
        return v

    @field_validator("datasets")
    @classmethod
    def _datasets(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("datasets must not be empty")
        return v


class OutputGuidance(BaseModel):
    format: str = "paper"
    max_words: int | None = None
    required_sections: list[str] = []
    emphasis: str | None = None
    constraints: list[str] = []


class RunSpec(BaseModel):
    run_id: str  # filename-safe; names the run's ledger and checkpoint files
    problem: ProblemSpec
    guidance: OutputGuidance
    budget: Budget
    models: dict[str, str] = {}  # stage -> backend name

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, v: str) -> str:
        if not _RUN_ID.fullmatch(v):
            raise ValueError("run_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
        return v

    @model_validator(mode="after")
    def _checks(self) -> RunSpec:
        b = self.budget
        if b.max_usd <= 0:
            raise ValueError("budget.max_usd must be positive")
        if b.spent_usd or b.elapsed_seconds or b.model_calls_used:
            raise ValueError("a new run's budget must start with nothing spent")
        unknown = set(self.models) - set(STAGES)
        if unknown:
            raise ValueError(f"models names unknown stages: {sorted(unknown)}")
        return self
