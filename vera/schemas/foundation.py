"""Foundation schemas: docs/03-interfaces.md, "Ledger" and "Budget"."""

from __future__ import annotations

from pydantic import BaseModel


class LedgerRecord(BaseModel):
    trace_id: str
    run_id: str
    component: str  # e.g. "p2.router", "p1.cite_check"
    backend: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float
    latency_ms: int
    timestamp: str  # ISO 8601
    error: str | None = None  # set when the call failed; the record is still written


class BudgetExceeded(RuntimeError):
    """A charge would cross a Budget limit. Budgets are hard limits: they raise, not warn."""


class Budget(BaseModel):
    max_usd: float
    max_wall_seconds: int
    max_model_calls: int | None = None
    spent_usd: float = 0.0
    elapsed_seconds: int = 0
    model_calls_used: int = 0

    def charge(self, usd: float, seconds: int = 0, calls: int = 1) -> None:
        """Record spend. Raises BudgetExceeded, leaving the budget unchanged, if any limit would be crossed."""
        if usd < 0 or seconds < 0 or calls < 0:
            raise ValueError("charges must be non-negative")
        crossed = []
        if self.spent_usd + usd > self.max_usd:
            crossed.append(f"usd {self.spent_usd + usd:.4f} > {self.max_usd}")
        if self.elapsed_seconds + seconds > self.max_wall_seconds:
            crossed.append(f"wall {self.elapsed_seconds + seconds}s > {self.max_wall_seconds}s")
        if self.max_model_calls is not None and self.model_calls_used + calls > self.max_model_calls:
            crossed.append(f"calls {self.model_calls_used + calls} > {self.max_model_calls}")
        if crossed:
            raise BudgetExceeded("; ".join(crossed))
        self.spent_usd += usd
        self.elapsed_seconds += seconds
        self.model_calls_used += calls
