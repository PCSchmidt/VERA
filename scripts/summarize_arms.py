"""Summarise the generator-comparison runs (docs/04 T9): cost, success and quality per arm, from the runs' own records.

Reads runs/gen-<arm>-<rep>/ (artifacts, gates.jsonl, audit_report.json, best_so_far.json) and the run ledgers, and
writes data/results/generator_comparison.json plus a table on stdout. Per run: spend by stage, tokens, wall time,
how many ideas were proposed / scored / implemented (valid first try, after a retry, never) / beat the baseline on
every dataset, the best held-out residual against the baseline's, whether the write-up met the guidance on the first
draft, and the audit's verdict and finding counts. Per arm: totals and means over its repeats. All runs start from the
same recorded baseline; the numbers are small-N and directional.

Usage: uv run python scripts/summarize_arms.py
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("p3.ideate", "p3.subset_exp", "p3.write_up", "p2.cheap_path")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def summarise_run(run_dir: Path) -> dict:
    run_id = run_dir.name
    ledger = [
        json.loads(ln)
        for ln in (ROOT / "data" / "ledger" / f"run_{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    best = read_json(run_dir / "best_so_far.json") or {}
    subset = read_json(run_dir / "artifacts" / "subset_exp.json") or {"log": {}, "results": {}}
    gate = read_json(run_dir / "artifacts" / "results_gate.json") or {}
    screen = read_json(run_dir / "artifacts" / "screen.json") or {}
    ideas = read_json(run_dir / "artifacts" / "ideas.json") or {"ideas": []}
    audit = read_json(run_dir / "artifacts" / "audit_final.json") or read_json(
        run_dir / "artifacts" / "audit_report.json"
    )
    check = read_json(run_dir / "artifacts" / "writeup_check.json") or {}
    results = (read_json(run_dir / "artifacts" / "results.json") or {}).get("results") or subset.get("results", {})
    by_stage = defaultdict(lambda: {"calls": 0, "cost": 0.0, "in": 0, "out": 0})
    for r in ledger:
        s = by_stage[r["component"]]
        s["calls"] += 1
        s["cost"] += r["cost_usd"]
        s["in"] += r["input_tokens"] or 0
        s["out"] += r["output_tokens"] or 0
    attempts = [len(v["attempts"]) for v in subset["log"].values()]
    first_try = sum(1 for v in subset["log"].values() if v["ok"] and len(v["attempts"]) == 1)
    base = results.get("TreeHFD (baseline)", {})
    deltas = {}
    for method, res in results.items():
        if method != "TreeHFD (baseline)":
            deltas[method] = {d: round(res[d]["residual_mse_pct"]["mean"] - base[d]["residual_mse_pct"]["mean"], 3)
                              for d in res if d in base}  # fmt: skip
    return {
        "run": run_id,
        "arm": run_id.removeprefix("gen-").rsplit("-", 1)[0],
        "models": sorted({r["model"] for r in ledger if r["component"].startswith("p3.")}),
        "completed": best.get("stop_reason") == "completed",
        "stop_reason": best.get("stop_reason"),
        "cost_usd": sum(r["cost_usd"] for r in ledger),
        "by_stage": {
            k: {"calls": v["calls"], "cost_usd": round(v["cost"], 6), "in": v["in"], "out": v["out"]}
            for k, v in by_stage.items()
        },  # fmt: skip
        "ideas_proposed": len(ideas["ideas"]),
        "ideas_selected": len(screen.get("selected", [])),
        "ideas_implemented_first_try": first_try,
        "ideas_implemented": sum(1 for v in subset["log"].values() if v["ok"]),
        "implementation_attempts": sum(attempts),
        "ideas_beating_baseline_everywhere": sum(1 for v in (gate.get("beats_all_datasets") or {}).values() if v),
        "held_out_delta_vs_baseline": deltas,
        "writeup_met_guidance": "write_up" in best.get("stages_completed", []),
        "writeup_problems": check.get("problems"),
        "audit": None
        if audit is None
        else {
            "overall": audit["overall"],
            "fail": sum(f["severity"] == "fail" for f in audit["findings"]),
            "warn": sum(f["severity"] == "warn" for f in audit["findings"]),
        },  # fmt: skip
    }


def main() -> None:
    runs = [summarise_run(p) for p in sorted((ROOT / "runs").glob("gen-*")) if (p / "best_so_far.json").exists()]
    arms = defaultdict(list)
    for r in runs:
        arms[r["arm"]].append(r)
    table = []
    for arm, rs in arms.items():
        done = [r for r in rs if r["completed"]]
        selected = sum(r["ideas_selected"] for r in rs)

        def stage_cost(component: str, rs: list = rs) -> float:
            return round(statistics.mean(r["by_stage"].get(component, {}).get("cost_usd", 0) for r in rs), 5)

        table.append(
            {
                "arm": arm,
                "runs": len(rs),
                "completed": len(done),
                "mean_cost_usd": round(statistics.mean(r["cost_usd"] for r in rs), 5),
                "mean_ideate_cost": stage_cost("p3.ideate"),
                "mean_code_cost": stage_cost("p3.subset_exp"),
                "mean_writeup_cost": stage_cost("p3.write_up"),
                "implemented_first_try": f"{sum(r['ideas_implemented_first_try'] for r in rs)}/{selected}",
                "implemented": f"{sum(r['ideas_implemented'] for r in rs)}/{selected}",
                "beat_baseline_everywhere": sum(r["ideas_beating_baseline_everywhere"] for r in rs),
                "audit": [r["audit"]["overall"] if r["audit"] else "none" for r in rs],
            }
        )
    out = ROOT / "data" / "results" / "generator_comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"arms": table, "runs": runs}, indent=1), encoding="utf-8")
    cols = list(table[0]) if table else []
    print(" | ".join(cols))
    for row in table:
        print(" | ".join(str(row[c]) for c in cols))


if __name__ == "__main__":
    main()
