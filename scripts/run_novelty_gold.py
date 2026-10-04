# ruff: noqa: E501
"""Run the audit's novelty judgement over the gold set (Increment 4, audit4_ready), live, on the cheap judge path.

  --split dev    free to repeat: the question is developed against dev only
  --split test   verifies the test pairs' hash and that the audit's source is exactly what was frozen
                 (`scripts/freeze_audit_v3.py`), refuses to run if results_test.json exists (a test set is spent by one run)

Each pair goes through `vera.audit.novelty.judge_pair`, the question the audit itself asks. A verdict "distinct" is correct on a
`distinct` pair and "not distinct" on a `not_distinct` pair; an unsure judge is counted as unsure, not as right. Reported per
label with Wilson 95% intervals, with the wrong pairs listed. The real loop ideas (label `unlabelled`) are also judged and
reported beside Chris's labels when `chris_labels.csv` exists. Writes results_<split>.json and a never-overwritten ledger.

Usage: uv run python scripts/run_novelty_gold.py --split dev
       uv run python scripts/run_novelty_gold.py --split test
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from vera.audit import seeded_v3
from vera.audit.novelty import judge_pair
from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "novelty_gold"
MIN_CONFIDENCE = 0.7


def test_hash(pairs: list[dict]) -> str:
    test = [p for p in pairs if p["split"] == "test"]
    return hashlib.sha256(json.dumps([{k: p[k] for k in ("id", "label", "idea", "prior_title")} for p in test], sort_keys=True).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    args = ap.parse_args()
    pairs = [json.loads(ln) for ln in (GOLD / "pairs.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    split = json.loads((GOLD / "split.json").read_text(encoding="utf-8"))
    out_file = GOLD / f"results_{args.split}.json"
    audit_hash = seeded_v3.audit_source_sha256(ROOT)
    if args.split == "test":
        if out_file.exists():
            raise SystemExit("results_test.json exists: the test set is spent by one run")
        if test_hash(pairs) != split["test_sha256"]:
            raise SystemExit("the test pairs changed since the split was fixed")
        if split.get("frozen_audit_sha256") != audit_hash:
            raise SystemExit(f"the audit's source ({audit_hash[:12]}) is not what was frozen ({str(split.get('frozen_audit_sha256'))[:12]})")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_noveltygold-{args.split}-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"noveltygold-{args.split}-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=1.0, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="audit.novelty")

    def ask(question, material):
        (v,) = judge.ask(material, [question])
        return v, v.confidence_source != "none" and v.confidence >= MIN_CONFIDENCE

    rows = []
    for p in pairs:
        if p["split"] not in (args.split, "chris"):
            continue
        distinct, verdict = judge_pair(p["idea"], p["prior_title"], p["prior_text"], ask)
        rows.append({"id": p["id"], "label": p["label"], "kind": p["kind"], "judged_distinct": distinct, "confidence": verdict.confidence})
    labelled = [r for r in rows if r["label"] != "unlabelled"]
    result: dict = {"split": args.split, "audit_sha256": audit_hash, "spend_usd": round(budget.spent_usd, 4), "ledger": ledger.path.relative_to(ROOT).as_posix()}
    for label, right in (("not_distinct", False), ("distinct", True)):
        sub = [r for r in labelled if r["label"] == label]
        k = sum(r["judged_distinct"] is right for r in sub)
        lo, hi = wilson(k, len(sub))
        result[label] = {"n": len(sub), "correct": k, "unsure": sum(r["judged_distinct"] is None for r in sub), "rate": round(k / len(sub), 4) if sub else None,
                         "ci95": [round(lo, 4), round(hi, 4)], "wrong": [r["id"] for r in sub if r["judged_distinct"] is (not right)]}  # fmt: skip
    real = [r for r in rows if r["label"] == "unlabelled"]
    result["real_ideas"] = {r["id"]: r["judged_distinct"] for r in real}
    for who, name in (("chris", "chris_labels.csv"), ("helper", "helper_labels.csv")):  # a person's labels and a model helper's, apart
        f = GOLD / name
        if not f.exists():
            continue
        rows_in = list(csv.DictReader(f.open(encoding="utf-8")))
        column = next(c for c in rows_in[0] if c.startswith("your_label"))  # the sheet's column name carries the choices
        labels = {r["id"]: r[column].strip() for r in rows_in}
        pairs_h = [(r, labels[r["id"]]) for r in real if labels.get(r["id"])]
        agree = sum((r["judged_distinct"] is True and lab == "distinct") or (r["judged_distinct"] is False and lab == "not_distinct") for r, lab in pairs_h)
        lo, hi = wilson(agree, len(pairs_h)) if pairs_h else (0, 0)
        result[who] = {"n": len(pairs_h), "agree": agree, "ci95": [round(lo, 4), round(hi, 4)]}
    out_file.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("real_ideas",)}, indent=1))


if __name__ == "__main__":
    main()
