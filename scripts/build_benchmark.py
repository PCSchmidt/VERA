"""Build the Increment 1 judge benchmark: items, split, test hash and label-check draw.

Reads (all local, no network, no model calls):
  data/cache/t3/<paper>/docling_tables.md   Docling tables for the T3 sample (scripts/t3_parse.py)
  data/cache/bench/refs/<paper>.json        GROBID reference lists (scripts/grobid_refs.py)

Writes:
  data/benchmark/items.jsonl         one BenchmarkItem per line (docs/03), sorted by id
  data/benchmark/split.json          seed, generator, counts, dev/test ids, test-split SHA-256
  data/benchmark/label_check.csv     items drawn by seed for Chris's label check (id, seed, verdict, note)
  data/benchmark/label_check_sheet.md  the drawn items in full, to check against

Splits are by unit, so near-identical items don't straddle dev and test:
a generated table (loop_gate) or a source paper (numeric, citation); about
1:2 dev:test. The split is fixed here, before any backend sees an item
(docs/06 §5). Once split.json exists, a rebuild that would change the test
split is refused unless --force; say why in the commit if you use it.

Usage: uv run python scripts/build_benchmark.py [--seed N] [--force]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.bench.build import (  # noqa: E402
    GENERATOR,
    citation_items,
    loop_items,
    numeric_items,
    parse_docling_tables,
    usable_title,
)
from vera.schemas import BenchmarkItem  # noqa: E402

T3 = ROOT / "data" / "cache" / "t3"
REFS = ROOT / "data" / "cache" / "bench" / "refs"
OUT = ROOT / "data" / "benchmark"
DEFAULT_SEED = 20261001
LABEL_CHECK_PER_TASK = 3
PREFIX = {"loop_gate": "loop", "numeric": "num", "citation": "cite"}


def test_hash(items: list[BenchmarkItem]) -> str:
    lines = [i.model_dump_json() for i in sorted(items, key=lambda i: i.id) if i.split == "test"]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def split_units(rng: random.Random, units: list, dev_fraction: float = 1 / 3) -> set:
    """Units for dev, drawn in random order until they hold about `dev_fraction` of the items."""
    counts = Counter(units)
    order = sorted(counts, key=str)
    rng.shuffle(order)
    target, dev, n = len(units) * dev_fraction, set(), 0
    for unit in order:
        if n + counts[unit] <= target + 2:
            dev.add(unit)
            n += counts[unit]
    return dev


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--force", action="store_true", help="allow a rebuild that changes the test split")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    loop = loop_items(rng, n_tables=20, seed=args.seed)

    tables = {d.name: parse_docling_tables((d / "docling_tables.md").read_text(encoding="utf-8")) for d in T3.iterdir()}
    numeric = numeric_items(rng, tables, n_bool=45, n_score=15, seed=args.seed)

    refs = {}
    for f in sorted(REFS.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        refs[data["paper"]] = data["refs"]
    rich = sorted(p for p, r in refs.items() if sum(usable_title(e["title"]) for e in r) >= 20)
    cite_papers = sorted(rng.sample(rich, 30))
    citation = citation_items(rng, refs, cite_papers, per_paper=2, window=25, seed=args.seed)

    items: list[BenchmarkItem] = []
    for task, pairs in [("loop_gate", loop), ("numeric", numeric), ("citation", citation)]:
        dev_units = split_units(rng, [u for u, _ in pairs])
        for n, (unit, item) in enumerate(pairs, 1):
            split = "dev" if unit in dev_units else "test"
            items.append(item.model_copy(update={"id": f"{PREFIX[task]}-{n:04d}", "split": split}))
    items = [BenchmarkItem.model_validate(i.model_dump()) for i in items]  # re-validate after copy
    items.sort(key=lambda i: i.id)

    digest = test_hash(items)
    split_file = OUT / "split.json"
    if split_file.exists() and not args.force:
        old = json.loads(split_file.read_text(encoding="utf-8"))
        if old["test_sha256"] != digest:
            sys.exit("refusing: this build changes the fixed test split (use --force and record why)")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
    counts = Counter((i.task, i.split) for i in items)
    types = Counter((i.task, i.question.type.value) for i in items)
    split = {
        "generator": GENERATOR,
        "seed": args.seed,
        "built": date.today().isoformat(),
        "units": "loop_gate: generated table; numeric and citation: source paper",
        "counts": {f"{t}/{s}": n for (t, s), n in sorted(counts.items())},
        "question_types": {f"{t}/{q}": n for (t, q), n in sorted(types.items())},
        "dev_ids": [i.id for i in items if i.split == "dev"],
        "test_ids": [i.id for i in items if i.split == "test"],
        "test_sha256": digest,
    }
    split_file.write_text(json.dumps(split, indent=1) + "\n", encoding="utf-8")

    check_seed = args.seed + 1
    draw_rng = random.Random(check_seed)
    drawn = []
    for task in PREFIX:
        drawn += draw_rng.sample([i for i in items if i.task == task], LABEL_CHECK_PER_TASK)
    check_csv = OUT / "label_check.csv"
    if not check_csv.exists() or args.force:
        with check_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["id", "seed", "verdict", "note"])
            w.writerows([i.id, check_seed, "", ""] for i in drawn)
        sheet = [
            "# Benchmark label check",
            "",
            f"Drawn with seed {check_seed} ({LABEL_CHECK_PER_TASK} per task). For each item, read the material and "
            "the question, and decide whether the recorded label is the correct answer. Record `correct` or "
            "`incorrect` (with a note) in `data/benchmark/label_check.csv`.",
        ]
        for i in drawn:
            sheet += [
                "",
                f"## {i.id} ({i.task}, {i.split}, {i.question.type.value})",
                "",
                f"**Question:** {i.question.text}",
                "",
                *([f"**Options:** {', '.join(i.question.options)}", ""] if i.question.options else []),
                *([f"**Scale:** {i.question.scale[0]}–{i.question.scale[1]}", ""] if i.question.scale else []),
                f"**Recorded label:** `{json.dumps(i.label)}` (built as: {i.construction['kind']})",
                "",
                "**Material:**",
                "",
                "```text",
                i.state,
                "```",
            ]
        (OUT / "label_check_sheet.md").write_text("\n".join(sheet) + "\n", encoding="utf-8")

    for k, v in split["counts"].items():
        print(f"{k:20} {v}")
    print(f"types: {split['question_types']}")
    print(f"test sha256: {digest}")


if __name__ == "__main__":
    main()
