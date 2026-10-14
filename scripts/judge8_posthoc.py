# ruff: noqa: E501
"""Post-hoc readings of the Increment 8 test run (not part of the frozen measurement; reads its stored answers only).

1. The labelled sample (`data/judge8/labels.json`, 45 test items, labelled blind by an OpenAI assistant at Chris's request):
   agreement of the reference and of each backend with those labels. `measure_judge8.py` was frozen before the labels
   existed and does not read them, so this is computed here (a deviation, stated in the review).
2. What a "no" is worth: for each question and backend, of the items the backend answers no (its modal answer), the share
   the reference also answers no (precision of a failure), and the share of the reference's no items it finds (recall).
   A sentence fails in the audit on a no, so this is the figure a red light rests on.
3. Confirming a no with the reference: the decided path's no items re-asked to the reference (simulated from the stored
   answers), and what that would cost per no at the reference's measured cost per verdict.

Writes data/results/judge8_test_posthoc.json. No model call.

    uv run python scripts/judge8_posthoc.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.bench.harness import load_recs  # noqa: E402
from vera.bench.metrics import modal_answers  # noqa: E402
from vera.bench.retest import wilson  # noqa: E402

SET = ROOT / "data" / "judge8"
KINDS = ("within_quote", "no_fact", "inference")


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n) if n else (0.0, 1.0)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 3), round(hi, 3)]}


def main() -> None:
    raw = SET / "raw" / "test"
    items = [json.loads(ln) for ln in (SET / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    kind_of = {i["id"]: i["kind"] for i in items if i["split"] == "test"}
    recs = {n: load_recs(raw / f"{n}.jsonl") for n in ("reference", "jev", "glm", "decided")}
    modes = {n: modal_answers(r) for n, r in recs.items()}
    ref = modes["reference"]
    labels = json.loads((SET / "labels.json").read_text(encoding="utf-8"))
    out: dict = {"labels_by": labels["labelled_by"], "labelled_sample": {}, "no_precision": {}, "confirm_with_reference": {}}
    for kind in KINDS:
        lab = {i: v for i, v in labels["labels"].items() if kind_of.get(i) == kind}
        out["labelled_sample"][kind] = {n: rate(sum(modes[n].get(i) is lab[i] for i in lab), len(lab)) for n in modes}
        ids = [i for i, k in kind_of.items() if k == kind]
        row = {}
        for n in ("jev", "glm", "decided"):
            no = [i for i in ids if modes[n].get(i) is False]
            ref_no = [i for i in ids if ref.get(i) is False]
            row[n] = {"precision_of_no": rate(sum(ref.get(i) is False for i in no), len(no)),
                      "recall_of_reference_no": rate(sum(modes[n].get(i) is False for i in ref_no), len(ref_no))}  # fmt: skip
        out["no_precision"][kind] = row
        ref_cost = sum(r.cost_usd for r in recs["reference"] if kind_of.get(r.item) == kind) / max(1, sum(1 for r in recs["reference"] if kind_of.get(r.item) == kind))
        no = [i for i in ids if modes["decided"].get(i) is False]
        out["confirm_with_reference"][kind] = {"decided_no_items": len(no), "reference_also_no": sum(ref.get(i) is False for i in no),
                                               "reference_cost_per_verdict_usd": round(ref_cost, 5)}  # fmt: skip
    (ROOT / "data" / "results" / "judge8_test_posthoc.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
