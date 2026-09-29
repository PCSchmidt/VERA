"""Research agent (P3) schemas: docs/03-interfaces.md, "Research agent"."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from vera.schemas.foundation import Budget
from vera.schemas.judge import Verdict


class StageResult(BaseModel):
    run_id: str
    stage: Literal["baseline", "ideate", "subset_exp", "full_exp", "ablation", "write_up", "audit"]
    artifact_ref: str  # path/ID of produced artifact
    producer_id: str
    gate: Verdict  # issued by a different component
    decision: Literal["accept", "refine", "reject"]
    metrics: dict[str, float] = {}
    budget_after: Budget
