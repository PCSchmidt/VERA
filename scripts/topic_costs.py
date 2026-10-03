"""The cost-per-topic table (Increment 3): what each topic's run cost by stage and component, from the ledgers.

For each topic it reads the topic run's checkpointed stage results (the spend after each stage, so a stage's cost is the
difference) and its ledger (calls, tokens and cost by component: the generator's stages and the judge path), and the
ledgers of the topic's earlier attempts (kept, never overwritten). For a topic carried through the research loop it adds
that run's report. Input share (input tokens over all tokens) and the largest prompt per component are what trade T7
needs. Writes data/results/topic_costs.json and docs/results/topic_costs.md.

Usage: uv run python scripts/topic_costs.py                      # reads data/topics/scope_<id>.json for the run ids
       uv run python scripts/topic_costs.py --loop tree-explain=topic-a-loop-1
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from vera.graph import run_config, sqlite_checkpointer

ROOT = Path(__file__).resolve().parents[1]
LEDGERS = ROOT / "data" / "ledger"


def read_ledger(run_id: str) -> list[dict]:
    path = LEDGERS / f"run_{run_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def by_component(records: list[dict]) -> list[dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                                                "largest_prompt_tokens": 0})  # fmt: skip
    for r in records:
        a = agg[r["component"]]
        a["calls"] += 1
        a["cost_usd"] += r["cost_usd"]
        a["input_tokens"] += r.get("input_tokens") or 0
        a["output_tokens"] += r.get("output_tokens") or 0
        a["largest_prompt_tokens"] = max(a["largest_prompt_tokens"], r.get("input_tokens") or 0)
    rows = []
    for name, a in sorted(agg.items()):
        total = a["input_tokens"] + a["output_tokens"]
        rows.append({"component": name, **a, "cost_usd": round(a["cost_usd"], 6),
                     "input_share": round(a["input_tokens"] / total, 3) if total else None})  # fmt: skip
    return rows


def stage_costs(run_id: str) -> list[dict]:
    """Per stage: the decision and the spend since the previous stage, from the run's checkpointed stage results."""
    run_dir = ROOT / "runs" / run_id
    saver = sqlite_checkpointer(run_dir / "checkpoints.sqlite")
    tup = saver.get_tuple(run_config(run_id))
    results = tup.checkpoint["channel_values"].get("stage_results", []) if tup else []
    out, previous = [], 0.0
    for s in results:
        spent = s["budget_after"]["spent_usd"]
        out.append({"stage": s["stage"], "decision": s["decision"], "cost_usd": round(spent - previous, 6),
                    "n_gates": len(s["gates"]), "reason": s.get("reason")})  # fmt: skip
        previous = spent
    return out


def earlier_attempts(run_id: str) -> list[str]:
    """Ledgers of the same run family with a lower trailing number (scope-x-1 for scope-x-2)."""
    stem, _, number = run_id.rpartition("-")
    if not number.isdigit():
        return []
    return [f"{stem}-{n}" for n in range(1, int(number)) if (LEDGERS / f"run_{stem}-{n}.jsonl").exists()]


def total(records: list[dict]) -> float:
    return round(sum(r["cost_usd"] for r in records), 4)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loop", action="append", default=[], metavar="TOPIC=RUN", help="a topic's research-loop run")
    args = ap.parse_args()
    loops = dict(item.split("=", 1) for item in args.loop)
    manifest = json.loads((ROOT / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    topics = {}
    for tid in manifest:
        scope = json.loads((ROOT / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run_id = scope["run_id"]
        ledger = read_ledger(run_id)
        earlier = {r: total(read_ledger(r)) for r in earlier_attempts(run_id)}
        entry = {"run_id": run_id, "total_usd": total(ledger), "earlier_attempts_usd": earlier,
                 "stages": stage_costs(run_id), "components": by_component(ledger)}  # fmt: skip
        if tid in loops:
            loop_ledger = read_ledger(loops[tid])
            entry["loop"] = {
                "run_id": loops[tid],
                "total_usd": total(loop_ledger),
                "components": by_component(loop_ledger),
            }
        topics[tid] = entry
    (ROOT / "data" / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "results" / "topic_costs.json").write_text(json.dumps(topics, indent=1), encoding="utf-8")

    lines = ["# Cost per topic", "",
             "From each run's own ledger (`data/ledger/run_<id>.jsonl`); regenerate with `scripts/topic_costs.py`.",
             "Stage costs are the spend between a stage's checkpointed result and the one before it; the judge path's",
             "calls (`p2.cheap_path`) inside a stage are part of that stage's cost. Input share is input tokens over",
             "all tokens.", "",
             "| topic | run | total (USD) | earlier attempts (USD) | loop run | loop (USD) | topic + loop (USD) |",
             "|---|---|---|---|---|---|---|"]  # fmt: skip
    for tid, e in topics.items():
        prior = sum(e["earlier_attempts_usd"].values())
        loop = e.get("loop")
        lines.append(f"| {tid} | {e['run_id']} | {e['total_usd']:.4f} | {prior:.4f} | "
                     f"{loop['run_id'] if loop else '-'} | {loop['total_usd'] if loop else '-'} | "
                     f"{e['total_usd'] + (loop['total_usd'] if loop else 0):.4f} |")  # fmt: skip
    for tid, e in topics.items():
        lines += [
            "",
            f"## {tid} ({e['run_id']})",
            "",
            "| stage | decision | cost (USD) | verdicts |",
            "|---|---|---|---|",
        ]
        lines += [f"| {s['stage']} | {s['decision']} | {s['cost_usd']:.4f} | {s['n_gates']} |" for s in e["stages"]]
        comp_tables = [("Components of the topic run", e["components"])]
        if e.get("loop"):
            comp_tables.append((f"Components of the research-loop run {e['loop']['run_id']}", e["loop"]["components"]))
        for title, comps in comp_tables:
            lines += ["", f"{title}:", "",
                      "| component | calls | cost (USD) | input tokens | output tokens | input share "
                      "| largest prompt (tokens) |",
                      "|---|---|---|---|---|---|---|"]  # fmt: skip
            lines += [f"| {c['component']} | {c['calls']} | {c['cost_usd']:.4f} | {c['input_tokens']} | "
                      f"{c['output_tokens']} | {c['input_share']} | {c['largest_prompt_tokens']} |"
                      for c in comps]  # fmt: skip
    out = ROOT / "docs" / "results" / "topic_costs.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"written: {out.relative_to(ROOT)}; totals: " + ", ".join(f"{t} ${e['total_usd']}" for t, e in topics.items())
    )


if __name__ == "__main__":
    main()
