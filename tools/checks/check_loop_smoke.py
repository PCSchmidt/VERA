"""Gate `stages_ready`: a live smoke run of the loop reached the write-up, with every call in the run's ledger.

Usage: check_loop_smoke.py <run_id> [--cap-usd 3.0] [--through write_up|audit]

Looks at runs/<run_id>/ and data/ledger/run_<run_id>.jsonl (both written by scripts/run_loop.py) and requires:
- the run finished all stages through `--through` (default write_up; audit adds the final audit and requires its
  report): best_so_far.json says "completed" with those stages done;
- the artifacts exist: baseline, ideas, screen, subset experiments, results.json, paper.md, and gates.jsonl;
- the ledger has records from the generator (p3.*) and the judge (p2.*), none missing a field, and its total is
  within the cap (the SPEC's debugging cap, $3.00);
- the run's recorded spend equals the ledger total (every call is in the ledger, none outside it);
- every judge verdict in gates.jsonl came from a component other than its producer (no self-grading).
The run's gates.jsonl and paper are git-ignored (runs/); the ledger is committed as the evidence.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

STAGES = ["baseline", "ideate", "subset_exp", "write_up", "audit"]
FIELDS = ["trace_id", "run_id", "component", "backend", "model", "cost_usd", "latency_ms", "timestamp"]


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--cap-usd", type=float, default=3.0)
    parser.add_argument("--through", choices=["write_up", "audit"], default="write_up")
    args = parser.parse_args()
    run = args.root / "runs" / args.run_id
    ledger = args.root / "data" / "ledger" / f"run_{args.run_id}.jsonl"

    best = run / "best_so_far.json"
    if not best.exists():
        block(f"{best} not found: run scripts/run_loop.py first")
    report = json.loads(best.read_text(encoding="utf-8"))
    wanted = STAGES[: STAGES.index(args.through) + 1]
    if report["stop_reason"] != "completed" or report["stages_completed"] != wanted:
        block(f"run {args.run_id} did not finish: {report['stop_reason']!r}, completed {report['stages_completed']}")

    needed = ["baseline", "ideas", "screen", "subset_exp", "results"]
    missing = [n for n in needed if not (run / "artifacts" / f"{n}.json").exists()]
    missing += [n for n in ("paper.md", "gates.jsonl") if not (run / n).exists()]
    if args.through == "audit":
        missing += [n for n in ("audit_report.json",) if not (run / "artifacts" / n).exists()]
        missing += [n for n in ("audit.md",) if not (run / n).exists()]
    if missing:
        block(f"run {args.run_id} is missing artifacts: {missing}")

    if not ledger.exists():
        block(f"{ledger} not found")
    records = [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for i, rec in enumerate(records):
        gap = [f for f in FIELDS if rec.get(f) in (None, "")]
        if gap:
            block(f"ledger record {i} is missing {gap}")
    components = {r["component"].split(".")[0] for r in records}
    if not {"p2", "p3"} <= components:
        block(f"the ledger must hold judge (p2.*) and generator (p3.*) calls, has {sorted(components)}")
    total = sum(r["cost_usd"] for r in records)
    if total > args.cap_usd:
        block(f"ledger total ${total:.4f} exceeds the cap ${args.cap_usd}")
    spent = report["budget"]["spent_usd"]
    if abs(spent - total) > 1e-6:
        block(f"the run's recorded spend ${spent:.6f} differs from its ledger ${total:.6f}: a call is unrecorded")

    for ln in (run / "gates.jsonl").read_text(encoding="utf-8").splitlines():
        v = json.loads(ln)["verdict"]
        if v["judge_id"] == v["producer_id"]:
            block(f"self-graded verdict on {v['question_id']}: {v['judge_id']}")
    ok(f"run {args.run_id}: all stages completed, {len(records)} ledgered calls, ${total:.4f} of ${args.cap_usd}")


if __name__ == "__main__":
    main()
