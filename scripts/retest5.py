# ruff: noqa: E501
"""The Increment 5 re-test of the judge on a larger set of the loop's gate decisions (T1 reverse-if (1), SPEC carry-in).

`build` assembles at least 150 labelled decisions (`loop.beats_baseline`, `loop.best_method`, `loop.baseline_reproduced`,
`loop.guidance_met`: each label is the answer computed from the table the judge reads), every item new: real decisions from
the runs that no earlier re-test used (the Increment 4 runs, the second problem's included) and perturbed copies of the
Increment 4 runs' result tables (the Increment 1 relations: clear win, near-tie, tie, loss) on both problems, so the set
includes a metric (MAE, one dataset) the earlier sets never had. Nothing is dropped silently: the split file counts every
record seen. All items are test items; the items' hash is written before any backend runs, and rebuilding refuses to
overwrite it. `run` asks the decided path (Jev, escalating to GLM; 3 repeats) and the reference (Claude Sonnet 5.5; 2
repeats) and reports item-level agreement of each with the labels and of the decided path with the reference, with
Wilson 95% intervals; reverse-if (1) fires when the decided path's agreement with the reference is below 95%.

Usage: uv run python scripts/retest5.py build
       uv run python scripts/retest5.py run
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

from vera.bench.candidates import make_backend
from vera.bench.harness import load_recs, run_backend
from vera.bench.metrics import backend_metrics, modal_answers, same
from vera.bench.retest import (
    digest,
    items_hash,
    load_gate_records,
    perturbed_items,
    real_items,
    to_item,
    wilson,
)
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.loop import credal, problem
from vera.schemas import BenchmarkItem, Budget

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "retest5"
REPEATS = {"decided": 3, "reference": 2}
TARGET = 150
SEED = 20261007
SOURCES = {"runs4-tree-explain": problem.TREEHFD, "runs4-credal": credal.CREDAL}  # run -> its problem kit
EARLIER = ("retest", "retest3")


class Decided:
    name, cost_rank = "decided", 1

    def __init__(self, ledger: Ledger, budget: Budget) -> None:
        self.path = cheap_path(ledger=ledger, budget=budget, component="p2.retest5")

    def ask(self, state, questions):
        return self.path.ask(state, questions)


def rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def earlier_keys() -> set[str]:
    keys = set()
    for name in EARLIER:
        for ln in (ROOT / "data" / name / "items.jsonl").read_text(encoding="utf-8").splitlines():
            it = json.loads(ln)
            keys.add(digest(it["question"]["id"], it["question"]["text"], it["state"]))
    return keys


def build() -> None:
    if (OUT / "split.json").exists():
        raise SystemExit("data/retest5/split.json exists: the set and its hash are fixed before any backend runs")
    records = load_gate_records(ROOT)
    real, coverage = real_items(records)
    old = earlier_keys()
    real = [r for r in real if digest(r["kind"], r["question"]["text"], r["material"]) not in old]
    coverage["real_new_items"] = len(real)
    rng = random.Random(SEED)
    pool, seen = [], {digest(r["kind"], r["question"]["text"], r["material"]) for r in real} | old
    for _ in range(200):
        for run, kit in SOURCES.items():
            data = json.loads((ROOT / "runs" / run / "artifacts" / "results.json").read_text(encoding="utf-8"))
            previous = problem.use(kit)
            try:
                src = {"run": run, "results": data["results"], "datasets": data["datasets"], "n_seeds": data["n_seeds"]}
                for raw in perturbed_items([src], rng, 1000):
                    key = digest(raw["kind"], raw["question"]["text"], raw["material"])
                    if key not in seen:
                        seen.add(key)
                        pool.append(raw)
            finally:
                problem.use(previous)
        if len(pool) + len(real) >= 4 * TARGET:
            break
    rng.shuffle(pool)
    need = max(0, TARGET - len(real))
    by_run = {r: [p for p in pool if p["runs"] == [r]] for r in SOURCES}  # the two problems stay balanced
    extra = [by_run[list(SOURCES)[i % len(SOURCES)]].pop() for i in range(need)]
    raws = sorted([*real, *extra], key=lambda r: (r["origin"], r["kind"], digest(json.dumps(r["question"]), r["material"])))
    items = []
    for i, raw in enumerate(raws):
        item = to_item(raw, i, "test")
        items.append(item.model_copy(update={"id": item.id.replace("retest-", "retest5-")}))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
    split = {"items": len(items), "test_sha256": items_hash(items), "coverage": coverage,
             "by_origin_kind": dict(Counter(f"{r['origin']}:{r['kind']}" for r in raws)),
             "by_label": dict(Counter(str(i.label) for i in items)),
             "note": "all items are evaluated (no dev split); fixed before any backend ran"}  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    print(json.dumps(split, indent=1))


def run() -> None:
    items = [BenchmarkItem.model_validate_json(ln) for ln in (OUT / "items.jsonl").read_text("utf-8").splitlines()]
    split = json.loads((OUT / "split.json").read_text(encoding="utf-8"))
    if items_hash(items) != split["test_sha256"]:
        raise SystemExit("the items changed since the hash was recorded")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_retest5-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"retest5-{n}", root=ROOT / "data" / "ledger")
    budget, ref_budget = Budget(max_usd=0.3, max_wall_seconds=7200), Budget(max_usd=1.2, max_wall_seconds=7200)
    decided = Decided(ledger, budget)
    reference = make_backend("sonnet-ref", ledger=ledger, budget=ref_budget, component="p2.retest5")
    raw = OUT / "raw"
    run_backend(decided, items, REPEATS["decided"], raw / "decided.jsonl", pause_s=3)
    run_backend(reference, items, REPEATS["reference"], raw / "reference.jsonl", pause_s=3)
    by_id = {i.id: i for i in items}
    d_recs, r_recs = load_recs(raw / "decided.jsonl"), load_recs(raw / "reference.jsonl")
    d_modes, r_modes = modal_answers(d_recs), modal_answers(r_recs)

    def summary(modes: dict) -> dict:
        ids = list(modes)
        kinds = sorted({by_id[i].construction["kind"] for i in ids})
        origins = sorted({by_id[i].construction["origin"] for i in ids})
        return {"agreement": rate([same(modes[i], by_id[i].label) for i in ids]),
                "by_kind": {k: rate([same(modes[i], by_id[i].label) for i in ids if by_id[i].construction["kind"] == k])
                            for k in kinds},
                "by_origin": {o: rate([same(modes[i], by_id[i].label) for i in ids if by_id[i].construction["origin"] == o])
                              for o in origins},
                "wrong": [i for i in ids if not same(modes[i], by_id[i].label)]}  # fmt: skip

    agree = rate([same(d_modes[i], r_modes[i]) for i in d_modes])
    results = {
        "items": len(items), "test_sha256": split["test_sha256"], "repeats": REPEATS,
        "decided_path": summary(d_modes) | {"metrics": backend_metrics(d_recs, r_modes), "agreement_with_reference": agree},
        "reference": summary(r_modes) | {"metrics": backend_metrics(r_recs, r_modes)},
        "t1_reverse_if_1": {"rule": "decided path below 95% agreement with the reference", "agreement_point": agree["rate"],
                            "ci95": agree["ci95"], "fired": agree["rate"] is not None and agree["rate"] < 0.95,
                            "fired_on_upper_bound": agree["ci95"][1] < 0.95},
        "spend_usd": {"decided": budget.spent_usd, "reference": ref_budget.spent_usd},
        "ledger": ledger.path.relative_to(ROOT).as_posix(),
    }  # fmt: skip
    (OUT / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for who in ("decided_path", "reference"):
        r = results[who]
        print(f"{who}: {r['agreement']['k']}/{r['agreement']['n']} wrong {r['wrong']}")
    print("decided vs reference:", agree, "| T1 reverse-if 1:", results["t1_reverse_if_1"])


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build()
    elif sys.argv[1:] == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
