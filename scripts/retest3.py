"""The Increment 3 re-test of the loop's gates on the new real decisions (SPEC "Judge re-test", second part).

`build` takes every `loop.*` decision with a programmatic (shadow) answer from this increment's loop runs (the runs
named on the command line), as the Increment 2 re-test did, but without perturbed copies: the point is the real
decisions, and at this size the result is descriptive. All items are evaluated (there is no dev split to tune on); the
items' hash is recorded before any backend runs. `run` asks the decided path (3 repeats) and the reference, Claude
Sonnet 5.5 (2 repeats), and reports item-level agreement with the labels with Wilson 95% intervals, the items each path
got wrong, the two confident misses of the Increment 2 re-test (retest-0008, retest-0038) with their tables, and the
distribution of `loop.idea_worth_run` scores (a Score with no computable label) beside what the ideas then did.

Usage: uv run python scripts/retest3.py build topic-a-loop-1 topic-a-loop-2
       uv run python scripts/retest3.py run
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from vera.bench.candidates import make_backend
from vera.bench.harness import load_recs, run_backend
from vera.bench.metrics import backend_metrics, modal_answers, same
from vera.bench.retest import is_current, items_hash, real_items, to_item, wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import BenchmarkItem, Budget

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "retest3"
REPEATS = {"decided": 3, "reference": 2}


class Decided:
    name, cost_rank = "decided", 1

    def __init__(self, ledger: Ledger, budget: Budget) -> None:
        self.path = cheap_path(ledger=ledger, budget=budget, component="p2.retest3")

    def ask(self, state, questions):
        return self.path.ask(state, questions)


def rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def gate_records(runs: list[str]) -> dict[str, list[dict]]:
    out = {}
    for run in runs:
        path = ROOT / "runs" / run / "gates.jsonl"
        out[run] = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return out


def build(runs: list[str]) -> None:
    if (OUT / "split.json").exists():
        raise SystemExit("data/retest3/split.json exists: the set and its hash are fixed before any backend runs")
    records = gate_records(runs)
    if not all(is_current(r) for r in records.values()):
        raise SystemExit("a run used an older baseline question wording")
    real, coverage = real_items(records)
    raws = sorted(real, key=lambda r: (r["kind"], r["material"]))
    items = [to_item(raw, i, "test") for i, raw in enumerate(raws)]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
    split = {"runs": runs, "items": len(items), "test_sha256": items_hash(items), "coverage": coverage,
             "by_kind": dict(Counter(i.construction["kind"] for i in items)),
             "note": "all items are evaluated (no dev split); fixed before any backend ran"}  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    print(json.dumps(split, indent=1))


def idea_scores(runs: list[str]) -> dict:
    """The loop.idea_worth_run scores of the runs, beside what each idea did (beat the baseline on every dataset)."""
    rows = []
    for run in runs:
        results = json.loads((ROOT / "runs" / run / "artifacts" / "results.json").read_text(encoding="utf-8"))
        ran = {m for m in results["results"] if not m.startswith("TreeHFD")}
        base = results["results"]["TreeHFD (baseline)"]
        for rec in gate_records([run])[run]:
            if rec["question"]["id"] != "loop.idea_worth_run":
                continue
            name = rec["material"].split("Candidate idea: ")[1].split("\n")[0]
            beat = None
            if name in ran:
                res = results["results"][name]
                beat = all(res[d]["residual_mse_pct"]["mean"] < base[d]["residual_mse_pct"]["mean"]
                           for d in results["datasets"])  # fmt: skip
            rows.append({"run": run, "idea": name, "score": rec["verdict"]["answer"], "ran": name in ran,
                         "beat_baseline_everywhere": beat})  # fmt: skip
    return {"rows": rows, "score_counts": dict(Counter(r["score"] for r in rows)),
            "ran": sum(r["ran"] for r in rows),
            "beat": sum(bool(r["beat_baseline_everywhere"]) for r in rows)}  # fmt: skip


def increment2_misses() -> list[dict]:
    items = {
        json.loads(ln)["id"]: json.loads(ln)
        for ln in (ROOT / "data" / "retest" / "items.jsonl").read_text("utf-8").splitlines()
    }
    out = []
    for iid in ("retest-0008", "retest-0038"):
        it = items[iid]
        rows = {}
        for who in ("decided", "reference"):
            raw = [
                json.loads(ln)
                for ln in (ROOT / "data" / "retest" / "raw" / f"{who}_test.jsonl").read_text("utf-8").splitlines()
            ]
            rows[who] = [(r["answer"], round(r["confidence"], 2)) for r in raw if r["item"] == iid]
        out.append({"id": iid, "label": it["label"], "question": it["question"]["text"], "state": it["state"],
                    "answers": rows})  # fmt: skip
    return out


def run() -> None:
    items = [BenchmarkItem.model_validate_json(ln) for ln in (OUT / "items.jsonl").read_text("utf-8").splitlines()]
    split = json.loads((OUT / "split.json").read_text(encoding="utf-8"))
    if items_hash(items) != split["test_sha256"]:
        raise SystemExit("the items changed since the hash was recorded")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_retest3-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"retest3-{n}", root=ROOT / "data" / "ledger")
    budget, ref_budget = Budget(max_usd=0.2, max_wall_seconds=3600), Budget(max_usd=0.5, max_wall_seconds=3600)
    decided = Decided(ledger, budget)
    reference = make_backend("sonnet-ref", ledger=ledger, budget=ref_budget, component="p2.retest3")
    raw = OUT / "raw"
    run_backend(decided, items, REPEATS["decided"], raw / "decided.jsonl", pause_s=3)
    run_backend(reference, items, REPEATS["reference"], raw / "reference.jsonl", pause_s=3)
    by_id = {i.id: i for i in items}
    d_recs, r_recs = load_recs(raw / "decided.jsonl"), load_recs(raw / "reference.jsonl")
    d_modes, r_modes = modal_answers(d_recs), modal_answers(r_recs)

    def summary(modes: dict) -> dict:
        ids = list(modes)
        kinds = sorted({by_id[i].construction["kind"] for i in ids})
        return {"agreement": rate([same(modes[i], by_id[i].label) for i in ids]),
                "by_kind": {k: rate([same(modes[i], by_id[i].label) for i in ids if by_id[i].construction["kind"] == k])
                            for k in kinds},
                "wrong": [i for i in ids if not same(modes[i], by_id[i].label)]}  # fmt: skip

    runs = split["runs"]
    results = {
        "items": len(items), "test_sha256": split["test_sha256"], "repeats": REPEATS, "runs": runs,
        "decided_path": summary(d_modes) | {"metrics": backend_metrics(d_recs, r_modes),
                                            "agreement_with_reference": rate(
                                                [same(d_modes[i], r_modes[i]) for i in d_modes])},
        "reference": summary(r_modes) | {"metrics": backend_metrics(r_recs, r_modes)},
        "t1_reverse_if_1": {"rule": "decided path below 95% agreement with the reference on the real decisions"},
        "increment2_confident_misses": increment2_misses(), "idea_worth_run": idea_scores(runs),
        "spend_usd": {"decided": budget.spent_usd, "reference": ref_budget.spent_usd},
        "ledger": ledger.path.relative_to(ROOT).as_posix(),
    }  # fmt: skip
    agree = results["decided_path"]["agreement_with_reference"]
    results["t1_reverse_if_1"] |= {"agreement_point": agree["rate"], "ci95": agree["ci95"],
                                   "fired": agree["rate"] is not None and agree["rate"] < 0.95,
                                   "fired_on_upper_bound": agree["ci95"][1] < 0.95}  # fmt: skip
    (OUT / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for who in ("decided_path", "reference"):
        r = results[who]
        print(f"{who}: {r['agreement']['k']}/{r['agreement']['n']} wrong {r['wrong']}")
    print("decided vs reference:", agree, "| T1 reverse-if 1:", results["t1_reverse_if_1"])
    print(
        "idea_worth_run:",
        results["idea_worth_run"]["score_counts"],
        "ran",
        results["idea_worth_run"]["ran"],
        "beat",
        results["idea_worth_run"]["beat"],
    )


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(sys.argv[2:])
    elif sys.argv[1:] == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
