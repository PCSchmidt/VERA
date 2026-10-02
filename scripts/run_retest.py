"""Run the judge re-test (docs/04 T1 reverse-if 1) on data/retest/items.jsonl and write data/retest/results.json.

Backends: the decided path (vera.judge.cheap_path: the loop's questions go straight to GLM-5.3 Flash at minimal
reasoning, as configured in the loop) and Claude Sonnet 5.5 as the reference (the Increment 1 configuration). The test
split is verified against its recorded hash first. The decided path runs 3 repeats on test and 1 on dev; the reference
2 repeats on test (the SPEC says 3; at three the reference's cost approached the $1 cap). Verdicts are resumable
(vera.bench.harness). Agreement is reported per item (the modal answer over repeats against the label) with Wilson 95%
intervals, which is the honest unit: repeats of one item are not independent evidence.

Usage: uv run python scripts/run_retest.py
"""

from __future__ import annotations

import json
from pathlib import Path

from vera.bench.candidates import make_backend
from vera.bench.harness import load_recs, run_backend
from vera.bench.metrics import backend_metrics, modal_answers, same
from vera.bench.retest import items_hash, wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import BenchmarkItem, Budget

ROOT = Path(__file__).resolve().parents[1]
RETEST = ROOT / "data" / "retest"
REPEATS = {"decided": {"test": 3, "dev": 1}, "reference": {"test": 2}}


class Decided:
    """The decided path as a JudgeBackend for the harness."""

    name = "decided"
    cost_rank = 1

    def __init__(self, ledger: Ledger, budget: Budget) -> None:
        self.path = cheap_path(ledger=ledger, budget=budget, component="p2.retest")

    def ask(self, state, questions):
        return self.path.ask(state, questions)


def rate(pairs: list[tuple[bool, str]], key: str | None = None) -> dict:
    sel = [ok for ok, k in pairs if key is None or k == key]
    k, n = sum(sel), len(sel)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def main() -> None:
    items = [
        BenchmarkItem.model_validate_json(ln)
        for ln in (RETEST / "items.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    split = json.loads((RETEST / "split.json").read_text(encoding="utf-8"))
    test = [i for i in items if i.split == "test"]
    dev = [i for i in items if i.split == "dev"]
    if items_hash(test) != split["test_sha256"]:
        raise SystemExit("the test items changed since the split was fixed: refusing to run")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_retest-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"retest-{n}", root=ROOT / "data" / "ledger")
    decided_budget, ref_budget = Budget(max_usd=0.3, max_wall_seconds=7200), Budget(max_usd=1.0, max_wall_seconds=7200)
    decided = Decided(ledger, decided_budget)
    reference = make_backend("sonnet-ref", ledger=ledger, budget=ref_budget, component="p2.retest")
    raw = RETEST / "raw"
    run_backend(decided, test, REPEATS["decided"]["test"], raw / "decided_test.jsonl", pause_s=3)
    run_backend(decided, dev, REPEATS["decided"]["dev"], raw / "decided_dev.jsonl", pause_s=3)
    run_backend(reference, test, REPEATS["reference"]["test"], raw / "reference_test.jsonl", pause_s=3)

    by_id = {i.id: i for i in test}
    d_recs, r_recs = load_recs(raw / "decided_test.jsonl"), load_recs(raw / "reference_test.jsonl")
    d_modes, r_modes = modal_answers(d_recs), modal_answers(r_recs)
    ref_metrics = backend_metrics(r_recs, r_modes)
    dec_metrics = backend_metrics(d_recs, r_modes)

    def info(i):
        return by_id[i].construction["kind"], by_id[i].construction["origin"]

    label_pairs = [(same(d_modes[i], by_id[i].label), info(i)[0]) for i in d_modes]
    origin_pairs = [(same(d_modes[i], by_id[i].label), info(i)[1]) for i in d_modes]
    ref_pairs = [(same(d_modes[i], r_modes[i]), info(i)[0]) for i in d_modes if i in r_modes]
    ref_label = [(same(r_modes[i], by_id[i].label), info(i)[0]) for i in r_modes]
    agree_ref = rate(ref_pairs)
    results = {
        "test_items": len(test), "test_sha256": split["test_sha256"], "repeats": REPEATS,
        "decided_path": {
            "agreement_with_label_item_level": rate(label_pairs),
            "by_kind": {k: rate(label_pairs, k) for k in sorted({k for _, k in label_pairs})},
            "by_origin": {o: rate(origin_pairs, o) for o in ("real", "perturbed")},
            "agreement_with_reference_item_level": agree_ref,
            "metrics": dec_metrics,
        },
        "reference": {"agreement_with_label_item_level": rate(ref_label), "metrics": ref_metrics},
        "dev_decided_agreement_with_label": rate(
            [(same(m, next(i for i in dev if i.id == k).label), "dev") for k, m in
             modal_answers(load_recs(raw / "decided_dev.jsonl")).items()]),  # fmt: skip
        "t1_reverse_if_1": {
            "rule": "decided path below 95% agreement with the reference on the real gate decisions",
            "agreement_point": agree_ref["rate"], "ci95": agree_ref["ci95"],
            "fired": agree_ref["rate"] is not None and agree_ref["rate"] < 0.95,
            "fired_on_upper_bound": agree_ref["ci95"][1] < 0.95,
        },
        "spend_usd": {"decided_and_dev": decided_budget.spent_usd, "reference": ref_budget.spent_usd},
        "ledger": ledger.path.relative_to(ROOT).as_posix(),
    }  # fmt: skip
    (RETEST / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(json.dumps({k: results[k] for k in ("t1_reverse_if_1", "spend_usd")}, indent=1))
    print("decided vs label:", results["decided_path"]["agreement_with_label_item_level"])
    print("reference vs label:", results["reference"]["agreement_with_label_item_level"])
    print("by kind:", {k: (v["k"], v["n"]) for k, v in results["decided_path"]["by_kind"].items()})
    print("by origin:", {k: (v["k"], v["n"]) for k, v in results["decided_path"]["by_origin"].items()})


if __name__ == "__main__":
    main()
