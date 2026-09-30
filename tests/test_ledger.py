"""FND-F-01: every model call writes a ledger record; budgets are checked before a call. No network."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vera.ledger import CallResult, Ledger, metered_call
from vera.schemas import Budget, BudgetExceeded

CHECK = Path(__file__).resolve().parents[1] / "tools" / "checks" / "check_vendor_imports.py"


def call_kwargs(ledger: Ledger, budget: Budget, estimate: float = 0.01) -> dict:
    return {"ledger": ledger, "budget": budget, "component": "p2.test", "backend": "fake",
            "model": "fake-model", "estimate_usd": estimate}  # fmt: skip


def ok_call() -> CallResult:
    return CallResult(text="yes", model="fake-model-v2", input_tokens=120, output_tokens=3, cost_usd=0.002)


def test_FND_F_01_every_call_writes_a_complete_record(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run1.jsonl"), Budget(max_usd=1.0, max_wall_seconds=60)
    metered_call(ok_call, trace_id="t-1", **call_kwargs(ledger, budget))
    metered_call(ok_call, **call_kwargs(ledger, budget))
    records = ledger.records()
    assert len(records) == 2
    r = records[0]
    assert (r.trace_id, r.run_id, r.component, r.backend, r.model) == (
        "t-1",
        "run1",
        "p2.test",
        "fake",
        "fake-model-v2",
    )
    assert (r.input_tokens, r.output_tokens, r.cost_usd, r.error) == (120, 3, 0.002, None)
    assert r.latency_ms >= 0 and r.timestamp
    assert records[1].trace_id and records[1].trace_id != "t-1"
    assert budget.spent_usd == pytest.approx(0.004) and budget.model_calls_used == 2


def test_FND_F_01_failed_call_is_recorded_and_reraised(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run.jsonl"), Budget(max_usd=1.0, max_wall_seconds=60)

    def boom() -> CallResult:
        raise ConnectionError("dns failure")

    with pytest.raises(ConnectionError):
        metered_call(boom, **call_kwargs(ledger, budget))
    (r,) = ledger.records()
    assert r.error == "ConnectionError: dns failure"
    assert (r.model, r.input_tokens, r.cost_usd) == ("fake-model", None, 0.0)
    assert budget.model_calls_used == 1


def test_FND_F_01_call_over_budget_raises_before_it_is_made(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run.jsonl"), Budget(max_usd=0.05, max_wall_seconds=60, spent_usd=0.04)
    made = []

    def call() -> CallResult:
        made.append(1)
        return ok_call()

    with pytest.raises(BudgetExceeded):
        metered_call(call, **call_kwargs(ledger, budget, estimate=0.02))
    assert made == [] and ledger.records() == []
    assert budget.spent_usd == 0.04 and budget.model_calls_used == 0


def test_FND_F_01_call_limit_is_enforced(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run.jsonl"), Budget(max_usd=1.0, max_wall_seconds=60, max_model_calls=1)
    metered_call(ok_call, **call_kwargs(ledger, budget))
    with pytest.raises(BudgetExceeded):
        metered_call(ok_call, **call_kwargs(ledger, budget))
    assert len(ledger.records()) == 1


def test_ledger_total_cost(tmp_path: Path) -> None:
    ledger, budget = Ledger(tmp_path / "run.jsonl"), Budget(max_usd=1.0, max_wall_seconds=60)
    for _ in range(3):
        metered_call(ok_call, **call_kwargs(ledger, budget))
    assert ledger.total_cost() == pytest.approx(0.006)


def run_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True, check=False
    )


def test_vendor_import_check_blocks_sdk_outside_backends(tmp_path: Path) -> None:
    (tmp_path / "vera" / "backends").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "vera" / "backends" / "openrouter.py").write_text("import openai\n", encoding="utf-8")
    assert run_check(tmp_path).returncode == 0
    (tmp_path / "vera" / "router.py").write_text("from anthropic import Anthropic\n", encoding="utf-8")
    result = run_check(tmp_path)
    assert result.returncode == 2 and "vera/router.py imports anthropic" in result.stderr
