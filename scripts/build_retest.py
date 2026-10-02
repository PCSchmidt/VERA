"""Build the judge re-test set from the loop's real gate decisions (docs/04 T1 reverse-if 1; vera/bench/retest.py).

Writes data/retest/items.jsonl and data/retest/split.json (the test items' SHA-256, the split by run and a coverage
count of every loop.* record seen, so none is dropped silently). The split file is written once, BEFORE any backend
is run on the test items; rebuilding refuses to overwrite it.

Usage: uv run python scripts/build_retest.py
"""

from __future__ import annotations

import json
from pathlib import Path

from vera.bench.retest import build_items, items_hash

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "retest"


def main() -> None:
    if (OUT / "split.json").exists():
        raise SystemExit(
            "data/retest/split.json exists: the set and its test hash are fixed. Delete it only to start a new set."
        )
    items, coverage = build_items(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
    test = [i for i in items if i.split == "test"]
    split = {
        "items": len(items), "test_items": len(test), "dev_items": len(items) - len(test),
        "test_sha256": items_hash(test), "coverage": coverage,
        "note": "fixed before any backend was run on a test item (docs/06 section 5)",
    }  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    print(json.dumps(split, indent=1))


if __name__ == "__main__":
    main()
