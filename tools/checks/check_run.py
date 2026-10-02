"""Gate `loop_run`: one complete end-to-end run of the loop, inside its budget, honestly recorded (SPEC "Complete run").

Usage: check_run.py [--prefix loop-] [--cap-usd 3.0] [--cap-wall 7200]

Looks at every run whose id starts with the prefix (a second attempt is allowed inside the increment cap) and passes if
at least one satisfies all of:
- it finished every stage through the audit (best_so_far.json: stop reason "completed", baseline, ideate, subset_exp,
  write_up and audit completed), with its artifacts (including audit_report.json) present;
- its ledger data/ledger/run_<id>.jsonl exists, every record carries the run id and the required fields, and its total
  equals the run's recorded spend (every call is in the ledger) and is within the run's Budget and the cap;
- its wall time is within the run's Budget and the cap;
- every judge verdict in gates.jsonl came from a component other than its producer (no self-grading), and the audit's
  gate is a rule (p1.audit_gate) distinct from the audit;
- the audit's overall result is recorded (green, amber or red is stated, not hidden; red does not pass a run as
  complete, since the audit failing stops it);
- data/results/run_<id>.json exists with the per-stage cost table, and its total matches the ledger.
Attempts that fail are listed in the message, so a pass never hides earlier failures.
"""

from __future__ import annotations

import json
from pathlib import Path

from _common import block, ok, repo_root_arg

STAGES = ["baseline", "ideate", "subset_exp", "write_up", "audit"]
FIELDS = ["trace_id", "run_id", "component", "backend", "model", "cost_usd", "latency_ms", "timestamp"]


def problems_with(root: Path, run_id: str, cap_usd: float, cap_wall: int) -> list[str]:
    run = root / "runs" / run_id
    ledger = root / "data" / "ledger" / f"run_{run_id}.jsonl"
    report_file = root / "data" / "results" / f"run_{run_id}.json"
    out: list[str] = []
    best = run / "best_so_far.json"
    if not best.exists():
        return [f"{best.relative_to(root)} not found"]
    best_report = json.loads(best.read_text(encoding="utf-8"))
    if best_report["stop_reason"] != "completed" or best_report["stages_completed"] != STAGES:
        out.append(f"did not finish: {best_report['stop_reason']!r}; completed {best_report['stages_completed']}")
    missing = [n for n in ("baseline", "ideas", "screen", "subset_exp", "results", "audit_report")
               if not (run / "artifacts" / f"{n}.json").exists()]  # fmt: skip
    missing += [n for n in ("paper.md", "gates.jsonl", "audit.md") if not (run / n).exists()]
    if missing:
        out.append(f"missing artifacts {missing}")
    if not ledger.exists():
        return [*out, f"ledger {ledger.relative_to(root)} not found"]
    records = [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for i, rec in enumerate(records):
        if rec.get("run_id") != run_id or any(rec.get(f) in (None, "") for f in FIELDS):
            out.append(f"ledger record {i} lacks the run id or a required field")
            break
    total = sum(r["cost_usd"] for r in records)
    budget = best_report["budget"]
    if abs(total - budget["spent_usd"]) > 1e-6:
        out.append(f"recorded spend ${budget['spent_usd']:.6f} differs from the ledger ${total:.6f}")
    if total > min(budget["max_usd"], cap_usd):
        out.append(f"spend ${total:.4f} exceeds the budget/cap")
    if budget["elapsed_seconds"] > min(budget["max_wall_seconds"], cap_wall):
        out.append(f"wall time {budget['elapsed_seconds']}s exceeds the budget/cap")
    gates = run / "gates.jsonl"
    if gates.exists():
        for ln in gates.read_text(encoding="utf-8").splitlines():
            v = json.loads(ln)["verdict"]
            if v["judge_id"] == v["producer_id"]:
                out.append(f"self-graded verdict on {v['question_id']}")
    audit_file = run / "artifacts" / "audit_report.json"
    if audit_file.exists():
        overall = json.loads(audit_file.read_text(encoding="utf-8")).get("overall")
        if overall not in ("green", "amber"):
            out.append(f"audit overall is {overall!r}")
    if not report_file.exists():
        out.append(f"{report_file.relative_to(root)} (per-stage cost table) not found")
    else:
        rep = json.loads(report_file.read_text(encoding="utf-8"))
        if abs(rep.get("total_cost_usd", -1) - total) > 1e-6 or not rep.get("by_component") or rep.get("audit") is None:
            out.append("the cost report does not match the ledger or lacks the cost table or the audit result")
        gate_judges = {s["gate_judge"] for s in rep.get("stages", []) if s["stage"] == "audit"}
        if gate_judges and gate_judges == {"p1.audit"}:
            out.append("the audit's gate was issued by the audit itself")
    return out


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--prefix", default="loop-")
    parser.add_argument("--cap-usd", type=float, default=3.0)
    parser.add_argument("--cap-wall", type=int, default=7200)
    args = parser.parse_args()
    runs = sorted(p.name for p in (args.root / "runs").glob(f"{args.prefix}*") if p.is_dir())
    if not runs:
        block(
            f"no run with the prefix {args.prefix!r} in runs/: launch it with scripts/run_loop.py --run-id loop-001 ..."
        )
    failed = {}
    for run_id in runs:
        found = problems_with(args.root, run_id, args.cap_usd, args.cap_wall)
        if not found:
            ok(f"complete run {run_id} (attempts: {len(runs)}, failed earlier or later: {sorted(failed)})")
            return
        failed[run_id] = found
    block("no complete run: " + "; ".join(f"{k}: {v[:3]}" for k, v in failed.items()))


if __name__ == "__main__":
    main()
