# ruff: noqa: E501
"""Draw the claims Chris re-labels (SPEC "Rubric scoring": at least 10 of the labelled real claims) without showing any label.

The 30 real claims of Increment 3 were labelled for support by an AI helper blind to every verdict
(data/claim_bench/real_claims_labels.csv). Chris re-labels a seeded sample of 12 of them from the same material the helper saw
(the claim and the passage that holds its quote), without seeing the helper's labels or any judge's verdict; agreement with the
helper is then reported with an interval (`scripts/record_relabels.py`). The sheet repeats excerpts of other people's papers and
is git-ignored (data/claim_bench/real_claims_sheet.csv is the source).

Writes data/claim_bench/relabel_sheet.csv (id, claim and passage, your_label).

Usage: uv run python scripts/build_relabel_sheet.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261014
N = 12


def main() -> None:
    sheet = list(csv.DictReader((ROOT / "data" / "claim_bench" / "real_claims_sheet.csv").open(encoding="utf-8", newline="")))
    drawn = sorted(random.Random(SEED).sample(sheet, N), key=lambda r: r["id"])
    out = ROOT / "data" / "claim_bench" / "relabel_sheet.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "claim and passage", "your_label (yes = the passage states or clearly implies the claim as written, "
                                                "including direction, numbers and qualifiers; no = it does not)"])
        for r in drawn:
            w.writerow([r["id"], r["material (claim and passage)"], ""])
    print(f"{N} claims drawn (seed {SEED}) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
