"""Build the seeded-fault set v2 (data/seeded_v2/) and fix its test split before the audit runs on it.

Documents: write-ups the loop produced (papers) and the topic runs' literature sections, from at least four source runs;
the split is by source run. For each document there is one unmodified control and one planted copy per applicable fault
type (vera.audit.seeded_v2). Writes

  data/seeded_v2/base/<doc>/...      the documents (a literature document's passages stay local: git-ignored)
  data/seeded_v2/items/<fault>/...   the planted copies
  data/seeded_v2/manifest.csv        one row per item (controls included)
  data/seeded_v2/split.json          the split, counts and the test items' SHA-256; `frozen_audit_sha256` is null until
                                     `scripts/run_seeded_v2.py --freeze` records the audit's own hash

Usage: uv run python scripts/build_seeded_v2.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

from vera.audit import seeded_v2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seeded_v2"
SEED = 20261008
DOCS = {  # id -> (kind, run directory, split)
    "gen-sonnet-2": ("paper", "runs/gen-sonnet-2", "dev"),
    "gen-sonnet-3": ("paper", "runs/gen-sonnet-3", "dev"),
    "gen-glm-sonnet-3": ("paper", "runs/gen-glm-sonnet-3", "dev"),
    "topic-credal-dro": ("lit", "runs/scope-credal-dro-2", "dev"),
    "loop-001": ("paper", "runs/loop-001", "test"),
    "gen-sonnet-4": ("paper", "runs/gen-sonnet-4", "test"),
    "gen-glm-sonnet-4": ("paper", "runs/gen-glm-sonnet-4", "test"),
    "gen-glm-3": ("paper", "runs/gen-glm-3", "test"),
    "topic-tree-explain": ("lit", "runs/scope-tree-explain-2", "test"),
    "topic-llm-judge-numbers": ("lit", "runs/scope-llm-judge-numbers-3", "test"),
}  # fmt: skip
PAPER_FILES = [("paper.md", "paper.md"), ("artifacts/results.json", "results.json"),
               ("retrieved.jsonl", "retrieved.jsonl")]  # fmt: skip
LIT_FILES = [("literature.md", "literature.md"), ("claims.jsonl", "claims.jsonl"), ("passages.jsonl", "passages.jsonl"),
             ("retrieved.jsonl", "retrieved.jsonl")]  # fmt: skip


def main() -> None:
    if (OUT / "split.json").exists():
        raise SystemExit("data/seeded_v2/split.json exists: the split is fixed once; delete it on purpose to rebuild")
    rows: list[dict] = []
    for doc, (kind, run, split) in DOCS.items():
        base = OUT / "base" / doc
        base.mkdir(parents=True, exist_ok=True)
        for src, name in PAPER_FILES if kind == "paper" else LIT_FILES:
            shutil.copy(ROOT / run / src, base / name)
        rows.append({"fault_id": f"{doc}:control", "doc": doc, "kind": kind, "fault_type": "control", "location": "",
                     "description": "unmodified document", "subtle": "", "split": split})  # fmt: skip
        for fault in seeded_v2.PAPER_FAULTS if kind == "paper" else seeded_v2.LIT_FAULTS:
            rng = random.Random(f"{SEED}:{doc}:{fault}")
            item = OUT / "items" / f"{doc}__{fault}"
            if kind == "paper":
                text = (base / "paper.md").read_text(encoding="utf-8")
                results = json.loads((base / "results.json").read_text(encoding="utf-8"))
                planted = seeded_v2.plant_paper(fault, text, results, rng)
                if planted is None:
                    continue
                new_text, location, description = planted
                item.mkdir(parents=True, exist_ok=True)
                (item / "paper.md").write_text(new_text, encoding="utf-8")
            else:
                text = (base / "literature.md").read_text(encoding="utf-8")
                claims = seeded_v2.load_jsonl(base / "claims.jsonl")
                planted = seeded_v2.plant_literature(fault, text, claims, rng)
                if planted is None:
                    continue
                new_text, new_claims, location, description = planted
                item.mkdir(parents=True, exist_ok=True)
                (item / "literature.md").write_text(new_text, encoding="utf-8")
                lines = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in new_claims)
                (item / "claims.jsonl").write_text(lines, encoding="utf-8")
            rows.append({"fault_id": f"{doc}:{fault}", "doc": doc, "kind": kind, "fault_type": fault,
                         "location": location, "description": description,
                         "subtle": "yes" if fault in seeded_v2.SUBTLE else "", "split": split})  # fmt: skip
    cols = ["fault_id", "doc", "kind", "fault_type", "location", "description", "subtle", "split"]
    with (OUT / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    test = [r for r in rows if r["split"] == "test"]
    split = {
        "seed": SEED, "rule": "by source run (document): dev and test share no document",
        "dev_docs": sorted(d for d, v in DOCS.items() if v[2] == "dev"),
        "test_docs": sorted(d for d, v in DOCS.items() if v[2] == "test"),
        "n_items": len(rows), "n_test_faults": sum(r["fault_type"] != "control" for r in test),
        "n_test_controls": sum(r["fault_type"] == "control" for r in test),
        "test_fault_types": sorted({r["fault_type"] for r in test if r["fault_type"] != "control"}),
        "test_sha256": test_hash(test), "frozen_audit_sha256": None,
        "note": "fixed before the audit ran on any test item; the audit's own hash is frozen before the test run",
    }  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    shown = ("n_items", "n_test_faults", "n_test_controls", "test_fault_types", "test_sha256")
    print(json.dumps({k: split[k] for k in shown}, indent=1))


def item_files(row: dict) -> list[Path]:
    if row["fault_type"] == "control":
        base = OUT / "base" / row["doc"]
        return [base / ("paper.md" if row["kind"] == "paper" else "literature.md")] + (
            [] if row["kind"] == "paper" else [base / "claims.jsonl"])  # fmt: skip
    item = OUT / "items" / f"{row['doc']}__{row['fault_type']}"
    return [item / "paper.md"] if row["kind"] == "paper" else [item / "literature.md", item / "claims.jsonl"]


def test_hash(rows: list[dict]) -> str:
    items = [{**r, "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in item_files(r)]} for r in rows]
    return seeded_v2.item_json(items)


if __name__ == "__main__":
    main()
