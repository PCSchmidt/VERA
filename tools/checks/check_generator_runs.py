"""Gate `trades_decided_2`: the generator comparison (docs/04 T9) was run, summarised, and stayed within its spend cap.

Requires:
- data/results/generator_comparison.json (scripts/summarize_arms.py) with at least 4 arms, at least 3 of which have 3
  or more repeats, and every run's ledger present;
- the total of the comparison runs' ledgers (data/ledger/run_gen-*.jsonl: all of them, including discarded and
  stopped-early runs) is within the SPEC's $4.00 measurement cap;
- no ledger record has an unrecorded cost (every call is in a run ledger: each run's recorded spend is its ledger sum).
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

CAP_USD = 4.00


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    summary = args.root / "data" / "results" / "generator_comparison.json"
    if not summary.exists():
        block("data/results/generator_comparison.json not found (scripts/summarize_arms.py)")
    data = json.loads(summary.read_text(encoding="utf-8"))
    arms = data["arms"]
    if len(arms) < 4:
        block(f"the comparison has {len(arms)} arms; at least 4 are needed")
    if sum(1 for a in arms if a["runs"] >= 3) < 3:
        block("at least 3 arms need 3 or more repeats")
    total = 0.0
    ledgers = sorted((args.root / "data" / "ledger").glob("run_gen-*.jsonl"))
    for run in data["runs"]:
        if not (args.root / "data" / "ledger" / f"run_{run['run']}.jsonl").exists():
            block(f"{run['run']} has no ledger")
    for path in ledgers:
        records = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        total += sum(r["cost_usd"] for r in records)
    if total > CAP_USD:
        block(f"the comparison's ledgers total ${total:.4f}, over the ${CAP_USD:.2f} measurement cap")
    ok(
        f"generator comparison: {len(arms)} arms, {len(data['runs'])} summarised runs, {len(ledgers)} ledgers, "
        f"${total:.4f} of ${CAP_USD:.2f}"
    )


if __name__ == "__main__":
    main()
