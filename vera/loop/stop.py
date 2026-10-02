"""Budget stop (RSH-P-01, RSH-F-06): on exhaustion the run stops and writes a best-so-far report.

`metered_call` already refuses a call that would cross a limit, before it is made. `guard_stage` wraps a graph
node so that the refusal ends the run cleanly instead of raising through the graph: the node returns a `stop`
entry, `route_after` sends the graph to its end, and `write_best_so_far` records why and what was reached.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from vera.schemas import STAGES, Budget, BudgetExceeded, RunSpec


class StopReport(BaseModel):
    run_id: str
    stop_reason: str  # e.g. "budget: usd 3.0021 > 3.0"
    stage_reached: str  # the stage that was running when the run stopped
    stages_completed: list[str]
    artifacts: dict[str, str]  # stage -> artifact reference, for the stages that finished
    budget: Budget
    timestamp: str


def guard_stage(stage: str, node: Callable[[dict], dict]) -> Callable[[dict], dict]:
    """Wrap a node: BudgetExceeded becomes a `stop` entry in the state instead of an exception."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")

    def guarded(state: dict) -> dict:
        if state.get("stop"):
            return {}  # already stopped: do nothing, spend nothing
        try:
            return node(state)
        except BudgetExceeded as exc:
            return {"stop": {"stage": stage, "reason": f"budget: {exc}"}}

    return guarded


def route_after(next_node: str, end: str) -> Callable[[Mapping[str, Any]], str]:
    """Conditional-edge function: go to `end` once the state carries a stop, else to `next_node`."""
    return lambda state: end if state.get("stop") else next_node


def write_best_so_far(state: Mapping[str, Any], spec: RunSpec, budget: Budget, path: Path) -> StopReport:
    """Write the best-so-far report for a stopped run and return it."""
    stop = state.get("stop") or {"stage": "none", "reason": "completed"}
    artifacts = state.get("artifacts") or {}
    done = [s for s in STAGES if s in artifacts]
    report = StopReport(
        run_id=spec.run_id,
        stop_reason=stop["reason"],
        stage_reached=stop["stage"],
        stages_completed=done,
        artifacts={s: artifacts[s] for s in done},
        budget=budget,
        timestamp=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    return report
