"""Validate agent-filled inventory rows and merge them into data/corpus_inventory.csv.

Inventory rows for Increment 0 were filled per domain into
data/cache/inventory_rows/<batch>.json (see data/inventory_task.md).
This script checks them before they reach the inventory:

- each gen_paper_id is a listed paper, and appears once across all batches;
- parent_title is one of the 107 candidates (data/parent_candidates.csv), and
  parent_venue / parent_id_arxiv_or_doi agree with data/parent_papers.csv;
- no parent is claimed by two generated papers (including rows already in
  the inventory);
- enum and URL values follow data/README.md.

With --write it merges valid rows into the inventory (rows not in any batch
are left as they are). It never writes if any problem is found.

Usage: uv run python scripts/merge_inventory_rows.py [--write]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "data" / "cache" / "inventory_rows"
INVENTORY = ROOT / "data" / "corpus_inventory.csv"
CSV_FIELDS = [
    "gen_code_url", "parent_title", "parent_venue", "parent_id_arxiv_or_doi", "parent_code_url",
    "reported_gain_pct", "compute_class", "candidate_for_p3", "notes",
]  # fmt: skip
COMPUTE = {"cpu", "single_gpu", "multi_gpu", "unknown"}


def is_url_or(value: str, *allowed: str) -> bool:
    return value in allowed or value.startswith(("http://", "https://"))


def validate(batch_rows: list[dict[str, str]], inventory: list[dict[str, str]],
             candidates: dict[str, dict[str, str]]) -> list[str]:  # fmt: skip
    problems = []
    listed = {r["gen_paper_id"] for r in inventory}
    counts = Counter(r.get("gen_paper_id") for r in batch_rows)
    problems += [f"{i}: appears {n} times across batches" for i, n in counts.items() if n > 1]
    for r in batch_rows:
        pid = r.get("gen_paper_id", "?")
        if pid not in listed:
            problems.append(f"{pid}: not a listed paper")
        missing = [f for f in CSV_FIELDS if f not in r or (f != "notes" and not str(r[f]).strip())]
        if missing:
            problems.append(f"{pid}: missing {missing}")
            continue
        cand = candidates.get(r["parent_title"])
        if cand is None:
            problems.append(f"{pid}: parent_title is not one of the 107 candidates: {r['parent_title'][:60]!r}")
        else:
            if r["parent_venue"] != cand["parent_venue"]:
                problems.append(f"{pid}: parent_venue {r['parent_venue']!r} != {cand['parent_venue']!r}")
            if r["parent_id_arxiv_or_doi"] != cand["paper_id"]:
                problems.append(f"{pid}: parent id {r['parent_id_arxiv_or_doi']!r} != {cand['paper_id']!r}")
        if r["compute_class"] not in COMPUTE:
            problems.append(f"{pid}: compute_class {r['compute_class']!r}")
        if r["candidate_for_p3"] not in {"yes", "no"}:
            problems.append(f"{pid}: candidate_for_p3 {r['candidate_for_p3']!r}")
        if not is_url_or(r["gen_code_url"], "none", "unknown") or not is_url_or(
            r["parent_code_url"], "none", "unknown"
        ):
            problems.append(f"{pid}: code URL must be a URL, none, or unknown")
        gain = r["reported_gain_pct"]
        if gain != "unknown" and not re.fullmatch(r"-?\d+(\.\d+)?", gain):
            problems.append(f"{pid}: reported_gain_pct {gain!r} is not a number or unknown")
        if "\n" in r["notes"] or '"' in r["notes"]:
            problems.append(f"{pid}: notes contain a line break or double quote")
    # one parent per generated paper, across the batches and rows already filled
    batch_ids = {r.get("gen_paper_id") for r in batch_rows}
    owners: dict[str, list[str]] = {}
    for r in list(batch_rows) + [r for r in inventory if r["gen_paper_id"] not in batch_ids and r["parent_title"]]:
        owners.setdefault(r.get("parent_title", ""), []).append(r.get("gen_paper_id", "?"))
    problems += [f"parent shared by {ids}: {t[:60]!r}" for t, ids in owners.items() if t and len(ids) > 1]
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="merge into the inventory if everything validates")
    args = parser.parse_args()

    with (ROOT / "data" / "parent_papers.csv").open(encoding="utf-8", newline="") as f:
        candidates = {r["parent_title"]: r for r in csv.DictReader(f)}
    with INVENTORY.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, inventory = list(reader.fieldnames or []), list(reader)
    batch_rows = [row for path in sorted(ROWS.glob("*.json")) for row in json.loads(path.read_text(encoding="utf-8"))]
    for row in batch_rows:
        for key, value in row.items():
            if isinstance(value, (int, float)):
                row[key] = str(value)

    problems = validate(batch_rows, inventory, candidates)
    filled = {r["gen_paper_id"] for r in inventory if r["parent_title"]} | {r["gen_paper_id"] for r in batch_rows}
    print(f"{len(batch_rows)} batch rows; {len(filled)}/{len(inventory)} inventory rows would be filled")
    for level in ("low", "medium"):
        ids = [r["gen_paper_id"] for r in batch_rows if r.get("confidence") == level]
        print(f"{level} confidence: {len(ids)} {ids}")
    for r in batch_rows:
        if r.get("flags"):
            print(f"FLAG {r['gen_paper_id']}: {r['flags']}")
    if problems:
        print(f"{len(problems)} problem(s):", *problems, sep="\n  ", file=sys.stderr)
        sys.exit(1)
    if args.write:
        by_id = {r["gen_paper_id"]: r for r in batch_rows}
        for row in inventory:
            if row["gen_paper_id"] in by_id:
                row.update({f: by_id[row["gen_paper_id"]][f] for f in CSV_FIELDS})
        with INVENTORY.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(inventory)
        print(f"merged {len(by_id)} rows into {INVENTORY.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
