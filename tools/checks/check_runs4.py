# ruff: noqa: E501
"""Gate `runs4`: the two end-to-end runs of Increment 4, from the confirmed question to the final audit.

Requires docs/results/runs4.json, listing exactly two runs (the tree-explain run with its protocol and the credal run), each with:
- every stage recorded: the run's report (docs/results/runs4/<id>/run_report.json) names a completed run, or one that stopped
  at a named stage with the reason (a run ending in budget exhaustion or a failed audit is a valid result if it says so, but the gate
  wants two runs that reached their final stage);
- the ledger (data/ledger/run_<id>.jsonl) summing to the recorded spend to the cent, and the spend within the run's cap;
- every gate verdict in the run's gates.jsonl from a component other than the producer of the material;
- an audit result stated (green, amber or red) with its counts, a per-stage cost table with the input share and the largest
  prompt of each component, and the paper committed (docs/results/runs4/<id>/paper.md, with its figures);
- the total of both runs within the increment's cap ($6.00), attempts included (every attempt is kept in the record).
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

CAP_USD = 6.0


def main() -> None:
    parser = repo_root_arg(__doc__)
    args = parser.parse_args()
    root = args.root
    index_file = root / "docs" / "results" / "runs4.json"
    if not index_file.exists():
        block("docs/results/runs4.json not found")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    runs = index["runs"]
    if sorted(r["problem"] for r in runs) != ["credal", "treehfd"]:
        block("runs4.json must list exactly one TreeHFD (tree-explain) run and one credal run")
    total = 0.0
    for r in runs:
        rid = r["id"]
        folder = root / "docs" / "results" / "runs4" / rid
        report = json.loads((folder / "run_report.json").read_text(encoding="utf-8")) if (folder / "run_report.json").exists() else block(f"{rid}: run_report.json not found")
        if not report["completed"] and not (report.get("stop") or {}).get("reason"):
            block(f"{rid}: neither completed nor stopped with a reason")
        if not report["completed"]:
            block(f"{rid}: the run did not reach its final stage ({report['stop']['stage']}: {report['stop']['reason'][:100]}); the gate wants two that did")
        ledger = root / report["ledger"]
        if not ledger.exists():
            block(f"{rid}: ledger {report['ledger']} not found")
        spent = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip())
        if abs(spent - r["spent_usd"]) > 0.005 or abs(spent - report["total_cost_usd"]) > 0.005:
            block(f"{rid}: the ledger sums to ${spent:.4f}, the record says ${r['spent_usd']}")
        if r["spent_usd"] > r["cap_usd"]:
            block(f"{rid}: spent ${r['spent_usd']} over its cap ${r['cap_usd']}")
        gates = folder / "gates.jsonl"
        if not gates.exists():
            block(f"{rid}: gates.jsonl not committed")
        for ln in gates.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                v = json.loads(ln)["verdict"]
                if v["judge_id"] == v["producer_id"]:
                    block(f"{rid}: a verdict was issued by the producer of the material ({v['judge_id']})")
        if not report.get("audit") or report["audit"]["overall"] not in ("green", "amber", "red"):
            block(f"{rid}: the audit result is not stated")
        components = report["by_component"]
        if not components or any("input_share" not in c or "max_input_tokens" not in c for c in components.values()):
            block(f"{rid}: the cost table lacks the input share or the largest prompt")
        if not (folder / "paper.md").exists():
            block(f"{rid}: the paper is not committed")
        total += spent
    if total > CAP_USD:
        block(f"both runs spent ${total:.2f}, over the ${CAP_USD:.2f} cap")
    ok("two runs reached their final stage: " + "; ".join(f"{r['id']} (${r['spent_usd']}, audit {json.loads((root / 'docs' / 'results' / 'runs4' / r['id'] / 'run_report.json').read_text(encoding='utf-8'))['audit']['overall']})" for r in runs) + f"; total ${total:.2f}")


if __name__ == "__main__":
    main()
