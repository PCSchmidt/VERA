"""Dependencies of the literature stage, injected so the whole stage runs offline with fakes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vera.graph import Judge
from vera.ledger import Ledger
from vera.loop.stages import Generator
from vera.schemas import Budget, RunSpec


@dataclass
class LitDeps:
    """The same shape `vera.loop.stages.ask_gate` and `stage_result` read (spec, judge, run_dir, budget...)."""

    spec: RunSpec
    generator: Generator
    judge: Judge
    budget: Budget
    run_dir: Path
    ledger: Ledger | None = None
    min_confidence: float = 0.7
    scope_cap_usd: float = 0.25  # spent on scoping before the user confirms; nothing more until then
    extra: dict[str, Any] = field(default_factory=dict)
