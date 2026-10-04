# ruff: noqa: E501
"""Record Chris's re-labels of the drawn real claims and report agreement with the helper's labels (Increment 4, rubric_scored).

Reads data/claim_bench/relabel_sheet.csv with the last column filled `yes` or `no`, writes
data/claim_bench/real_claims_relabels.csv (id, label, by, at; committed: no passage text) and data/results/relabel_agreement.json
(agreement with the AI helper's labels in real_claims_labels.csv, with a Wilson 95% interval, and the ids where they differ).
Refuses if any row is blank or the file already exists (a re-label is recorded once; to change one, say so in the review).

Usage: uv run python scripts/record_relabels.py --by Chris
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path

from vera.bench.retest import wilson

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--by", required=True)
    args = ap.parse_args()
    out = ROOT / "data" / "claim_bench" / "real_claims_relabels.csv"
    if out.exists():
        raise SystemExit("the re-labels are already recorded")
    rows = list(csv.reader((ROOT / "data" / "claim_bench" / "relabel_sheet.csv").open(encoding="utf-8", newline="")))[1:]
    labels = {r[0]: r[-1].strip().lower() for r in rows}
    if any(v not in ("yes", "no") for v in labels.values()):
        raise SystemExit("every row needs `yes` or `no` in the last column")
    helper = {r["id"]: r["supported"].strip().lower() for r in csv.DictReader((ROOT / "data" / "claim_bench" / "real_claims_labels.csv").open(encoding="utf-8", newline=""))}
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "label", "by", "at"])
        for i, v in labels.items():
            w.writerow([i, v, args.by, stamp])
    agree = sum(labels[i] == helper[i] for i in labels)
    lo, hi = wilson(agree, len(labels))
    report = {"by": args.by, "at": stamp, "n": len(labels), "agree_with_helper": agree, "rate": round(agree / len(labels), 4),
              "ci95": [round(lo, 4), round(hi, 4)], "differ": sorted(i for i in labels if labels[i] != helper[i]),
              "helper": "an AI helper blind to every verdict (real_claims_labels.csv), not a person"}  # fmt: skip
    (ROOT / "data" / "results" / "relabel_agreement.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
