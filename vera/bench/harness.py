"""Benchmark harness (JDG-F-06): run one backend over the test split with repeats, resumably.

Each verdict is appended to `data/benchmark/raw/<backend>.jsonl` as soon as
it returns, one line per (item, repeat). A rerun skips pairs already there,
so a crashed or interrupted run resumes without paying for completed calls
again. Repeats are the outer loop, so a partial run covers every item evenly.

A call that raises is retried (this machine has intermittent DNS failures);
if it still fails, a row with `error` set, answer "" and confidence 0 is
written, which the metrics count as an unusable answer. Every attempt is in
the ledger (`metered_call`). `BudgetExceeded` stops the backend's run.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from vera.bench.metrics import Rec
from vera.schemas import BenchmarkItem, BudgetExceeded, JudgeBackend

RETRIES = 2


def done_pairs(path: Path) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {(r["item"], r["repeat"]) for r in rows}


def run_backend(
    backend: JudgeBackend,
    items: Sequence[BenchmarkItem],
    repeats: int,
    out: Path,
    *,
    progress: Callable[[str], None] = print,
    pause_s: float = 5.0,
) -> int:
    """Ask every item `repeats` times; returns the number of new rows written."""
    out.parent.mkdir(parents=True, exist_ok=True)
    done = done_pairs(out)
    written = 0
    with out.open("a", encoding="utf-8") as fh:
        for repeat in range(repeats):
            for item in items:
                if (item.id, repeat) in done:
                    continue
                row = {"backend": backend.name, "item": item.id, "repeat": repeat, "task": item.task,
                       "label": item.label}  # fmt: skip
                for attempt in range(RETRIES + 1):
                    try:
                        (v,) = backend.ask(item.state, [item.question])
                    except BudgetExceeded:
                        raise
                    except Exception as err:  # noqa: BLE001 - the ledger has the failed call
                        if attempt < RETRIES:
                            time.sleep(pause_s)
                            continue
                        error = f"{type(err).__name__}: {err}"[:300]
                        row |= {"answer": "", "confidence": 0.0, "source": "none", "cost_usd": 0.0,
                                "latency_ms": 0, "trace_id": "", "error": error}  # fmt: skip
                        break
                    row |= {"answer": v.answer, "confidence": v.confidence, "source": v.confidence_source or "none",
                            "cost_usd": v.cost_usd, "latency_ms": v.latency_ms, "trace_id": v.trace_id,
                            "error": None}  # fmt: skip
                    break
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                written += 1
            progress(f"{backend.name}: repeat {repeat + 1}/{repeats} done")
    return written


def load_recs(path: Path) -> list[Rec]:
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [Rec(r["backend"], r["item"], r["repeat"], r["task"], r["label"], r["answer"], float(r["confidence"]),
                r["source"], float(r["cost_usd"]), int(r["latency_ms"])) for r in rows]  # fmt: skip
