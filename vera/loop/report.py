"""The per-stage cost and outcome report of a finished run: data/results/run_<run_id>.json.

Written by scripts/run_loop.py at the end of every run (complete, stopped or failed). It is the table the Increment 2
review reads (SPEC "Complete run"): what each stage cost, which model did what, each gate's decision and verdict, the
audit's result and the headline numbers. Costs come from the run's own ledger, so they sum to what was spent.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from vera.loop import tables
from vera.loop.stages import LoopDeps


def _gate(stage: dict) -> dict:
    """The verdict that decided the stage (the first one when it was accepted), as StageResult.gate does."""
    deciding = stage.get("deciding_gates") or [0]
    return stage["gates"][deciding[0]]


def build_report(deps: LoopDeps, state: dict) -> dict:
    ledger = deps.ledger.records() if deps.ledger is not None else []
    by_component: dict[str, dict] = defaultdict(
        lambda: {"calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "max_input_tokens": 0}
    )
    for r in ledger:
        c = by_component[r.component]
        c["calls"] += 1
        c["cost_usd"] += r.cost_usd
        c["input_tokens"] += r.input_tokens or 0
        c["output_tokens"] += r.output_tokens or 0
        c["max_input_tokens"] = max(c["max_input_tokens"], r.input_tokens or 0)  # the largest prompt of the component
    stages = [
        {
            "stage": s["stage"], "decision": s["decision"], "producer": s["producer_id"],
            "gate_question": _gate(s)["question_id"], "gate_answer": _gate(s)["answer"],
            "gate_judge": _gate(s)["judge_id"], "n_gates": len(s["gates"]), "metrics": s["metrics"],
            "spent_usd_after": s["budget_after"]["spent_usd"],
        }
        for s in state.get("stage_results", [])
    ]  # fmt: skip
    audit_path = deps.run_dir / "artifacts" / "audit_report.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else None
    results = state.get("results") or {}
    headline = {}
    for method, res in results.items():
        headline[method] = {
            d: round(v[tables.PRIMARY]["mean"], 3)
            for d, v in res.items()
            if d in deps.datasets and v.get(tables.PRIMARY)
        }
    stop = state.get("stop")
    return {
        "run_id": deps.spec.run_id,
        "models": deps.spec.models,
        "completed": stop is None,
        "stop": stop,
        "total_cost_usd": round(sum(r.cost_usd for r in ledger), 6),
        "budget": {
            "max_usd": deps.budget.max_usd,
            "spent_usd": deps.budget.spent_usd,
            "max_wall_seconds": deps.budget.max_wall_seconds,
            "elapsed_seconds": deps.budget.elapsed_seconds,
        },  # fmt: skip
        "by_component": {
            k: {
                **v,
                "cost_usd": round(v["cost_usd"], 6),
                "input_share": round(v["input_tokens"] / max(v["input_tokens"] + v["output_tokens"], 1), 3),
            }
            for k, v in sorted(by_component.items())
        },  # fmt: skip
        "stages": stages,
        "audit": None
        if audit is None
        else {
            "overall": audit["overall"],
            "fail": sum(f["severity"] == "fail" for f in audit["findings"]),
            "warn": sum(f["severity"] == "warn" for f in audit["findings"]),
            "info": sum(f["severity"] == "info" for f in audit["findings"]),
            "checks_skipped": audit["checks_skipped"],
        },  # fmt: skip
        "best_idea": state.get("best"),
        "held_out_residual_mse_pct": headline,
        "baseline_name": tables.BASELINE,
        "ledger": f"data/ledger/run_{deps.spec.run_id}.jsonl",
    }


def write_report(deps: LoopDeps, state: dict, root: Path) -> Path:
    out = root / "data" / "results" / f"run_{deps.spec.run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_report(deps, state), indent=1, ensure_ascii=False), encoding="utf-8")
    return out
