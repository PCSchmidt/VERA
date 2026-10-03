"""Gate `topic_runs`: three topics run to their final stage, costs measured, one carried through the research loop.

For every topic in data/topics/manifest.json (run id from data/topics/scope_<id>.json):
- data/results/topic_run_<run_id>.json (scripts/topic_costs.py): the run completed, with every stage of the
  literature stage recorded (scope, retrieve, read, synthesize, and parent for an empirical question), each stage
  accepted, and every verdict issued by a component other than the stage's producer;
- the record's ledger total equals the run's ledger file, and the topic's spend is within the per-topic cap;
- an audit of the literature section, stated as green, amber or red (red is allowed: it is reported, not hidden);
- data/topics/parent_<id>.json: a pick or a reason (never both, never neither), and for an empirical topic the user's
  reading of it (`user_review`: right or wrong, with a name and a date);
and overall:
- docs/results/topic_costs.md naming every topic, and the sum over topics and loop runs within the cap ($8);
- for the topic with a harness, a research-loop run (data/results/topic_costs.json names it) whose report
  (data/results/run_<loop>.json) shows every loop stage (baseline, ideate, subset_exp, write_up, audit) with the ledger
  total equal to its ledger file and an audit result stated.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

LIT_STAGES = ["scope", "retrieve", "read", "synthesize"]
LOOP_STAGES = ["baseline", "ideate", "subset_exp", "write_up", "audit"]


def ledger_total(root, run_id: str) -> float:
    path = root / "data" / "ledger" / f"run_{run_id}.jsonl"
    if not path.exists():
        block(f"ledger of run {run_id!r} not found")
    return sum(json.loads(ln)["cost_usd"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=8.0)
    parser.add_argument("--topic-cap-usd", type=float, default=2.0)
    args = parser.parse_args()
    root = args.root
    topics = json.loads((root / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    costs_md = root / "docs" / "results" / "topic_costs.md"
    costs_json = root / "data" / "results" / "topic_costs.json"
    if not costs_md.exists() or not costs_json.exists():
        block("docs/results/topic_costs.md or data/results/topic_costs.json not found (scripts/topic_costs.py)")
    costs = json.loads(costs_json.read_text(encoding="utf-8"))
    md = costs_md.read_text(encoding="utf-8")
    spent, summary, loop_run = 0.0, [], None
    for tid in topics:
        if tid not in md:
            block(f"docs/results/topic_costs.md does not name topic {tid!r}")
        scope = json.loads((root / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        empirical = scope["empirical"] in (True, "True", "true")
        run_id = scope["run_id"]
        rec_path = root / "data" / "results" / f"topic_run_{run_id}.json"
        if not rec_path.exists():
            block(f"{tid}: data/results/topic_run_{run_id}.json not found (scripts/topic_costs.py)")
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        if not rec["completed"]:
            block(f"{tid}: run {run_id} did not complete ({rec['stop_reason']})")
        want = LIT_STAGES + (["parent"] if empirical else [])
        got = [s["stage"] for s in rec["stages"]]
        missing = [s for s in want if s not in got]
        if missing:
            block(f"{tid}: stages not recorded: {missing}")
        for s in rec["stages"]:
            if s["decision"] != "accept":
                block(f"{tid}: stage {s['stage']} was {s['decision']}, not accepted")
            for g in s["gates"]:
                if g["judge"] == s["producer"] or (g.get("producer") not in (None, s["producer"])):
                    block(f"{tid}: a verdict in stage {s['stage']} is not independent of its producer")
        total = ledger_total(root, run_id)
        if abs(total - rec["ledger_total_usd"]) > 1e-3:
            block(f"{tid}: recorded spend ${rec['ledger_total_usd']} differs from the ledger's ${total:.4f}")
        if total > args.topic_cap_usd:
            block(f"{tid}: ${total:.3f} spent, over the ${args.topic_cap_usd} per-topic cap")
        spent += total
        if not rec["audit"] or rec["audit"]["overall"] not in ("green", "amber", "red"):
            block(f"{tid}: no audit result (scripts/audit_topic.py, then scripts/topic_costs.py)")
        parent_path = root / "data" / "topics" / f"parent_{tid}.json"
        if not parent_path.exists():
            block(f"{tid}: data/topics/parent_{tid}.json not found (scripts/review_parent.py)")
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
        if (parent["picked"] is None) == (parent["none_fits_reason"] is None):
            block(f"{tid}: parent selection must pick a candidate or give a reason, exactly one")
        review = parent.get("user_review")
        read = review and review.get("by") and review.get("at") and isinstance(review.get("right"), bool)
        if empirical and not read:
            block(f"{tid}: the user's reading of the parent selection is not recorded (scripts/review_parent.py)")
        entry = costs.get(tid, {})
        if entry.get("loop"):
            loop_run = (tid, entry["loop"]["run_id"])
        summary.append(f"{tid} {rec['audit']['overall']}")
    if loop_run is None:
        block("no topic has a research-loop run (scripts/topic_costs.py --loop TOPIC=RUN)")
    tid, loop_id = loop_run
    report_path = root / "data" / "results" / f"run_{loop_id}.json"
    if not report_path.exists():
        block(f"{tid}: data/results/run_{loop_id}.json not found (written by scripts/run_loop.py)")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    stages = [s["stage"] for s in report["stages"]]
    missing = [s for s in LOOP_STAGES if s not in stages]
    if missing:
        block(f"{tid}: the loop run {loop_id} shows no stage {missing}")
    if not report.get("audit") or report["audit"]["overall"] not in ("green", "amber", "red"):
        block(f"{tid}: the loop run {loop_id} has no audit result")
    loop_total = ledger_total(root, loop_id)
    if abs(loop_total - report["total_cost_usd"]) > 1e-3:
        block(f"{tid}: the loop report's ${report['total_cost_usd']} differs from the ledger's ${loop_total:.4f}")
    spent += loop_total
    if spent > args.cap_usd:
        block(f"${spent:.3f} spent across the topic runs, over the ${args.cap_usd} cap")
    ok(f"3 topics ({', '.join(summary)}); loop run {loop_id} audit {report['audit']['overall']}; spent ${spent:.3f}")


if __name__ == "__main__":
    main()
