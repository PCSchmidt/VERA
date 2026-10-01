"""JDG-F-06 harness: resumable runs, retries, error rows and hard budget stops, with a fake backend. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vera.bench.harness import done_pairs, load_recs, run_backend
from vera.schemas import BenchmarkItem, BudgetExceeded, Question, QuestionType, Verdict

Q = Question(id="b", type=QuestionType.BOOLEAN, text="?")
ITEMS = [BenchmarkItem(id=f"i{k}", task="citation", split="test", question=Q, state=f"s{k}", label=k % 2 == 0,
                       construction={"kind": "true"}, generator="t") for k in range(3)]  # fmt: skip


class Fake:
    name, cost_rank = "fake", 1

    def __init__(self, fail_times: int = 0, budget_after: int | None = None) -> None:
        self.calls, self.fail_times, self.budget_after = 0, fail_times, budget_after

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        self.calls += 1
        if self.budget_after is not None and self.calls > self.budget_after:
            raise BudgetExceeded("usd")
        if self.calls <= self.fail_times:
            raise ConnectionError("getaddrinfo failed")
        return [Verdict(question_id=Q.id, answer=True, confidence=0.8, confidence_source="self_report", backend="fake",
                        escalated=False, cost_usd=0.001, latency_ms=50, trace_id="t", judge_id="p2.judge")]  # fmt: skip


def rows(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


def test_JDG_F_06_harness_writes_every_item_and_repeat(tmp_path: Path) -> None:
    out = tmp_path / "fake.jsonl"
    assert run_backend(Fake(), ITEMS, 2, out, progress=lambda m: None) == 6
    assert [(r["item"], r["repeat"]) for r in rows(out)][:4] == [("i0", 0), ("i1", 0), ("i2", 0), ("i0", 1)]
    recs = load_recs(out)
    assert len(recs) == 6 and recs[1].label is False and recs[0].answer is True


def test_JDG_F_06_harness_resumes_without_repeating_calls(tmp_path: Path) -> None:
    out = tmp_path / "fake.jsonl"
    with pytest.raises(BudgetExceeded):
        run_backend(Fake(budget_after=4), ITEMS, 2, out, progress=lambda m: None)
    assert len(done_pairs(out)) == 4
    again = Fake()
    assert run_backend(again, ITEMS, 2, out, progress=lambda m: None) == 2
    assert again.calls == 2 and len(rows(out)) == 6


def test_JDG_F_06_harness_retries_then_records_an_unusable_row(tmp_path: Path) -> None:
    out = tmp_path / "fake.jsonl"
    run_backend(Fake(fail_times=2), ITEMS[:1], 1, out, progress=lambda m: None, pause_s=0)
    (ok,) = rows(out)
    assert ok["error"] is None and ok["answer"] is True  # two failures, third attempt succeeded
    out2 = tmp_path / "fake2.jsonl"
    run_backend(Fake(fail_times=99), ITEMS[:1], 1, out2, progress=lambda m: None, pause_s=0)
    (bad,) = rows(out2)
    assert "getaddrinfo" in bad["error"] and bad["source"] == "none" and bad["confidence"] == 0.0
