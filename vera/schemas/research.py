"""Research agent (P3) schemas: docs/03-interfaces.md, "Research agent"."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

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
