"""Research agent (P3) schemas: docs/03-interfaces.md, "Research agent"."""

from __future__ import annotations

import re
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

from vera.schemas.foundation import Budget
from vera.schemas.judge import SelfGradingError, Verdict
from vera.schemas.literature import Topic


class StageResult(BaseModel):
    run_id: str
    stage: Literal[
        "scope", "retrieve", "read", "synthesize", "parent",
        "baseline", "ideate", "subset_exp", "full_exp", "ablation", "write_up", "audit",
    ]  # fmt: skip
    artifact_ref: str  # path/ID of produced artifact
    producer_id: str
    gates: list[Verdict] = Field(min_length=1)  # every verdict the stage asked, each from a different component
    deciding_gates: list[int] = []  # indices into `gates` of the verdicts that decided a reject or refine
    reason: str | None = None  # a deterministic cause of a reject (no verdict decided it)
    decision: Literal["accept", "refine", "reject"]
    metrics: dict[str, float] = {}
    budget_after: Budget

    @model_validator(mode="before")
    @classmethod
    def _legacy_single_gate(cls, data: object) -> object:
        # Schemas up to 0.8 stored one `gate`; it becomes the only (and, for a reject, the deciding) verdict.
        if isinstance(data, dict) and "gate" in data and "gates" not in data:
            data = {k: v for k, v in data.items() if k != "gate"} | {"gates": [data["gate"]]}
            if data.get("decision") != "accept":
                data.setdefault("deciding_gates", [0])
        return data

    @property
    def gate(self) -> Verdict:
        """The verdict that decided the stage, or the first one when it was accepted."""
        return self.gates[self.deciding_gates[0] if self.deciding_gates else 0]

    @model_validator(mode="after")
    def _gates_not_self_issued(self) -> StageResult:
        # Verdict's own rule can't see this stage's producer when a verdict's producer_id is empty.
        for gate in self.gates:
            if gate.judge_id == self.producer_id:
                raise SelfGradingError(f"stage {self.stage!r}: gate issued by its own producer ({self.producer_id!r})")
            if gate.producer_id is not None and gate.producer_id != self.producer_id:
                raise SelfGradingError(
                    f"stage {self.stage!r}: gate judges {gate.producer_id!r}'s work, "
                    f"but the stage was produced by {self.producer_id!r}"
                )
        if any(not 0 <= i < len(self.gates) for i in self.deciding_gates):
            raise ValueError(f"stage {self.stage!r}: deciding_gates names a verdict that does not exist")
        if self.decision == "reject" and not (self.deciding_gates or self.reason):
            raise ValueError(f"stage {self.stage!r}: a reject must name the verdict (or the reason) that caused it")
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
    problem: ProblemSpec | None = None  # none until a parent problem is chosen (a topic run, Increment 3)
    guidance: OutputGuidance
    budget: Budget
    models: dict[str, str] = {}  # stage -> backend name
    topic: Topic | None = None  # set when the run starts from a topic (Increment 3)

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, v: str) -> str:
        if not _RUN_ID.fullmatch(v):
            raise ValueError("run_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
        return v

    @model_validator(mode="after")
    def _checks(self) -> RunSpec:
        if self.problem is None and self.topic is None:
            raise ValueError("a run needs a problem, a topic, or both")
        b = self.budget
        if b.max_usd <= 0:
            raise ValueError("budget.max_usd must be positive")
        if b.spent_usd or b.elapsed_seconds or b.model_calls_used:
            raise ValueError("a new run's budget must start with nothing spent")
        unknown = set(self.models) - set(STAGES)
        if unknown:
            raise ValueError(f"models names unknown stages: {sorted(unknown)}")
        return self
