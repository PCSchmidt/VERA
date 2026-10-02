"""Build the claim-support benchmark from the topic runs and fix its test split before any backend sees it.

Writes data/claim_bench/:
  items.jsonl           the items (git-ignored: they quote other people's papers)
  split.json            counts, the split rule and the test items' SHA-256 (committed)
  label_check_sheet.csv 9 items drawn by seed for a person to label, without their labels (git-ignored)
  label_check.csv       the person's verdicts (filled after the sheet; committed)

Usage: uv run python scripts/build_claim_benchmark.py [--dev-topic credal-dro]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from vera.bench.claims import SEED, base_pairs, build_items, items_hash

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "claim_bench"
LABEL_CHECK_SEED = 20261007
CHECK_PER_GROUP = 3  # supported, other-paper or other-passage, reversed or altered number


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev-topic", default="credal-dro")
    args = ap.parse_args()
    if (OUT / "split.json").exists():
        raise SystemExit("data/claim_bench/split.json exists: the split is fixed once; delete it on purpose to rebuild")
    bases = base_pairs(ROOT)
    items = build_items(bases, args.dev_topic)
    test = [i for i in items if i.split == "test"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
    split = {
        "seed": SEED, "rule": f"by topic: dev = {args.dev_topic}, test = the other topics",
        "n_items": len(items), "n_test": len(test), "n_dev": len(items) - len(test),
        "by_kind": dict(Counter(i.construction["kind"] for i in items)),
        "by_split_label": dict(Counter(f"{i.split}:{i.label}" for i in items)),
        "by_topic": dict(Counter(i.construction["topic"] for i in items)),
        "test_sha256": items_hash(test),
        "note": "fixed before any backend ran on a test item (docs/06 section 5)",
    }  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    rng = random.Random(LABEL_CHECK_SEED)
    groups = {"supported": ["supported"], "wrong place": ["other_paper", "other_passage"],
              "changed claim": ["reversed", "altered_number"]}  # fmt: skip
    drawn = []
    for kinds in groups.values():
        pool = [i for i in items if i.construction["kind"] in kinds]
        drawn += rng.sample(pool, min(CHECK_PER_GROUP, len(pool)))
    rng.shuffle(drawn)
    with (OUT / "label_check_sheet.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "material (claim and passage)", "supported (yes/no)"])
        for i in drawn:
            w.writerow([i.id, i.state, ""])
    shown = ("n_items", "n_test", "n_dev", "by_kind", "by_split_label", "test_sha256")
    print(json.dumps({k: split[k] for k in shown}, indent=1))
    print(f"label check: {len(drawn)} items in data/claim_bench/label_check_sheet.csv")


if __name__ == "__main__":
    main()
