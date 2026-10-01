"""Backend smoke run (JDG-F-04 demonstration; gate backends_live): 10 dev items per backend, <= $1.00.

Draws 10 items from the benchmark's dev split by seed (stratified over the
three tasks; the test split is never touched), asks every candidate backend
(vera/bench/candidates.py) each item once, and writes:

  data/ledger/smoke.jsonl           one LedgerRecord per model call, failed calls included
  data/ledger/smoke_verdicts.jsonl  one line per (backend, item): the Verdict and the item's label

All calls share one Budget of $1.00 that raises before a call that could
cross it. A failed call is recorded and the run moves on to the next item.
Ledgers are append-only (FND-F-01): the script never deletes or
overwrites them. If the smoke ledger already exists, it refuses to start
unless --append is given, which adds to the existing run (same items, same
seed); move the old files aside by hand to start a new smoke run.

Usage: uv run python scripts/smoke_run.py [--backends mimo-flash jev ...] [--seed N]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.bench.candidates import NAMES, make_backend  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.schemas import BenchmarkItem, Budget, BudgetExceeded  # noqa: E402

ITEMS = ROOT / "data" / "benchmark" / "items.jsonl"
LEDGER = ROOT / "data" / "ledger" / "smoke.jsonl"
VERDICTS = ROOT / "data" / "ledger" / "smoke_verdicts.jsonl"
PER_TASK = {"loop_gate": 4, "numeric": 3, "citation": 3}
MAX_USD = 1.00


def draw(seed: int) -> list[BenchmarkItem]:
    items = [BenchmarkItem.model_validate_json(ln) for ln in ITEMS.read_text(encoding="utf-8").splitlines() if ln]
    dev = [i for i in items if i.split == "dev"]
    rng = random.Random(seed)
    return [x for task, n in PER_TASK.items() for x in rng.sample([i for i in dev if i.task == task], n)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backends", nargs="+", default=NAMES, choices=NAMES)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--append", action="store_true", help="add to the existing smoke ledger and verdicts")
    args = parser.parse_args()

    sample = draw(args.seed)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not args.append and (LEDGER.exists() or VERDICTS.exists()):
        sys.exit(f"refusing: {LEDGER.name} exists and ledgers are append-only; use --append or move it aside")
    ledger = Ledger(LEDGER, run_id="smoke")
    budget = Budget(max_usd=MAX_USD, max_wall_seconds=3600)
    budget.charge(ledger.total_cost(), calls=0)  # an appended run shares the $1.00 with the earlier one
    with VERDICTS.open("a" if args.append else "w", encoding="utf-8") as out:
        for name in args.backends:
            backend = make_backend(name, ledger=ledger, budget=budget, component="p2.smoke")
            right = failed = malformed = 0
            for item in sample:
                try:
                    (verdict,) = backend.ask(item.state, [item.question])
                except BudgetExceeded:
                    raise
                except Exception as err:  # noqa: BLE001 - recorded in the ledger by metered_call
                    failed += 1
                    print(f"  {name} {item.id}: {type(err).__name__}: {str(err)[:160]}", flush=True)
                    continue
                right += verdict.answer == item.label
                malformed += verdict.confidence_source == "none"
                row = {"backend": name, "item": item.id, "task": item.task, "label": item.label,
                       "verdict": verdict.model_dump(mode="json")}  # fmt: skip
                out.write(json.dumps(row) + "\n")
            answered = len(sample) - failed
            print(f"{name:15} agree {right}/{answered}  no usable answer {malformed}  failed {failed}  "
                  f"spent so far ${budget.spent_usd:.4f}")  # fmt: skip
    print(f"total ${ledger.total_cost():.4f} over {len(ledger.records())} calls (budget ${MAX_USD:.2f})")


if __name__ == "__main__":
    main()
