"""Cost/latency/trace ledger (FND-F-01). Every model call writes a LedgerRecord.

Every backend call goes through `metered_call`, which:

1. checks the call's worst-case cost estimate against the `Budget` *before*
   the call (on a copy, so the budget is unchanged if it would not fit);
2. times the call and writes a `LedgerRecord`, also when the call fails;
3. charges the actual cost and wall time to the `Budget`.

The estimate must be an upper bound (prompt tokens x input price plus
max_tokens x output price): if a call still costs more than the budget has
left, the money is already spent, so `charge` raises after the record is
written and the run stops there.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vera.schemas import Budget, LedgerRecord


@dataclass
class CallResult:
    """What a backend's raw call returns to `metered_call`."""

    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)  # e.g. logprobs; not written to the ledger


class Ledger:
    """Append-only JSONL file of LedgerRecords for one run."""

    def __init__(self, path: Path, run_id: str | None = None) -> None:
        self.path = Path(path)
        self.run_id = run_id or self.path.stem
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: LedgerRecord) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")
            fh.flush()

    def records(self) -> list[LedgerRecord]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [LedgerRecord.model_validate(json.loads(line)) for line in lines if line.strip()]

    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.records())


def new_trace_id() -> str:
    return uuid.uuid4().hex


def metered_call(
    call: Callable[[], CallResult],
    *,
    ledger: Ledger,
    budget: Budget,
    component: str,
    backend: str,
    model: str,
    estimate_usd: float,
    trace_id: str | None = None,
) -> CallResult:
    """Run one model call under the budget, recording it in the ledger. See the module docstring."""
    trace_id = trace_id or new_trace_id()
    budget.model_copy().charge(estimate_usd, seconds=0, calls=1)  # raises before any spend if it can't fit
    start = time.perf_counter()
    result: CallResult | None = None
    error: str | None = None
    try:
        result = call()
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised
        error = f"{type(exc).__name__}: {exc}"[:500]
        raise
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        ledger.write(
            LedgerRecord(
                trace_id=trace_id,
                run_id=ledger.run_id,
                component=component,
                backend=backend,
                model=result.model if result else model,
                input_tokens=result.input_tokens if result else None,
                output_tokens=result.output_tokens if result else None,
                cost_usd=result.cost_usd if result else 0.0,
                latency_ms=latency_ms,
                timestamp=dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds"),
                error=error,
            )
        )
        budget.charge(result.cost_usd if result else 0.0, seconds=round(latency_ms / 1000), calls=1)
    return result
