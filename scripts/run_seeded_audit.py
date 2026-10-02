"""Run the audit over a split of the seeded-fault set, live: the real judge path and the real bibliographic sources.

Writes data/seeded/results_<split>.json (per-item results and the summary) and a never-overwritten ledger
data/ledger/run_seeded-<split>-<n>.jsonl. Detection = the audit raised at least one `fail` finding on a planted fault;
a `fail` on an unmodified control is a false positive. The test split is verified against its recorded hash first
(vera.audit.seeded.verify_split) and is meant to be run once, after the audit was developed against dev (docs/06 §5).

Usage: uv run python scripts/run_seeded_audit.py --split dev
       uv run python scripts/run_seeded_audit.py --split test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera.audit.bibliography import SourceLookup
from vera.audit.seeded import evaluate
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "results" / "treehfd_baseline_target.json"
MIN_CONFIDENCE = 0.7  # the loop's bar for a confident verdict


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--max-usd", type=float, default=0.5)
    args = ap.parse_args()

    n = 1
    while (ROOT / "data" / "ledger" / f"run_seeded-{args.split}-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"seeded-{args.split}-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=args.max_usd, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget)

    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        verdict = verdict.model_copy(update={"producer_id": "p3.write_up"})
        return verdict, verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE

    target = json.loads(TARGET.read_text(encoding="utf-8"))
    rows, summary = evaluate(ROOT, args.split, ask=ask, lookup=SourceLookup(), target=target)
    summary |= {"spent_usd": budget.spent_usd, "ledger": ledger.path.relative_to(ROOT).as_posix()}
    out = ROOT / "data" / "seeded" / f"results_{args.split}.json"
    out.write_text(json.dumps({"split": args.split, "summary": summary, "items": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for r in rows:
        mark = (
            "ok "
            if (r["detected"] == (r["fault_type"] != "control"))
            else "MISS"
            if r["fault_type"] != "control"
            else "FP  "
        )
        print(f"{mark} {r['fault_id']:42} overall={r['overall']:5} fail={r['n_fail']} warn={r['n_warn']}")


if __name__ == "__main__":
    main()
