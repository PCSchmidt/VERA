"""The benchmark is built, split and label-checked (gate benchmark_labeled; SPEC "Benchmark set").

Blocks unless:
- data/benchmark/items.jsonl has items for the three tasks (loop_gate,
  numeric, citation), all three question types, and every item a split;
- data/benchmark/split.json records the test split's ids and SHA-256, and both
  match items.jsonl (the hash is over the test items' lines, sorted by id,
  joined by newlines — docs/03 `BenchmarkItem`);
- data/benchmark/label_check.csv (id, seed, verdict, note) has at least 3
  checked items per task, each drawn by a recorded seed and naming a real
  item, with verdict `correct`, `incorrect` or `fixed` (an incorrect label
  since fixed and its generator re-checked; say how in the note), and no
  `incorrect` left.

Chris's human approval follows; this check only says the evidence is there.
"""

from __future__ import annotations

import csv
import hashlib
import json

from _common import block, ok, repo_root_arg

TASKS = {"loop_gate", "numeric", "citation"}
TYPES = {"choice", "score", "boolean"}
MIN_CHECKED = 3
VERDICTS = {"correct", "incorrect", "fixed"}


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    bench = root / "data" / "benchmark"
    items_path, split_path, check_path = bench / "items.jsonl", bench / "split.json", bench / "label_check.csv"
    for path in (items_path, split_path, check_path):
        if not path.exists():
            block(f"{path.relative_to(root).as_posix()} not found")

    lines = [ln for ln in items_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    try:
        items = [json.loads(ln) for ln in lines]
    except json.JSONDecodeError as err:
        block(f"items.jsonl is not JSON lines: {err}")
    ids = [i.get("id") for i in items]
    if len(set(ids)) != len(ids):
        block("items.jsonl has duplicate ids")
    tasks = {i.get("task") for i in items}
    if tasks != TASKS:
        block(f"tasks are {sorted(map(str, tasks))}; expected {sorted(TASKS)}")
    types = {i.get("question", {}).get("type") for i in items}
    if not TYPES <= types:
        block(f"question types missing: {sorted(TYPES - types)}")
    bad_split = [i["id"] for i in items if i.get("split") not in {"dev", "test"}]
    if bad_split:
        block(f"items without a dev/test split: {bad_split[:5]}")

    split = json.loads(split_path.read_text(encoding="utf-8"))
    test = sorted((i["id"], ln) for i, ln in zip(items, lines, strict=True) if i["split"] == "test")
    if not test:
        block("the test split is empty")
    if sorted(split.get("test_ids", [])) != [i for i, _ in test]:
        block("split.json test_ids do not match the test items in items.jsonl")
    digest = hashlib.sha256("\n".join(ln for _, ln in test).encode("utf-8")).hexdigest()
    if split.get("test_sha256") != digest:
        block(f"test split hash {digest[:12]}… differs from split.json's {str(split.get('test_sha256'))[:12]}…")

    task_of = {i["id"]: i["task"] for i in items}
    with check_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    checked = {t: 0 for t in TASKS}
    for row in rows:
        rid, verdict = (row.get("id") or "").strip(), (row.get("verdict") or "").strip().lower()
        if not verdict:
            continue
        if rid not in task_of:
            block(f"label_check.csv names an unknown item: {rid!r}")
        if not (row.get("seed") or "").strip():
            block(f"label_check.csv row {rid}: no seed recorded")
        if verdict not in VERDICTS:
            block(f"label_check.csv row {rid}: verdict {verdict!r} not one of {sorted(VERDICTS)}")
        if verdict == "incorrect":
            block(f"label_check.csv row {rid}: label marked incorrect and not yet fixed")
        if verdict == "fixed" and not (row.get("note") or "").strip():
            block(f"label_check.csv row {rid}: 'fixed' needs a note saying what changed")
        checked[task_of[rid]] += 1
    short = {t: n for t, n in checked.items() if n < MIN_CHECKED}
    if short:
        block(f"fewer than {MIN_CHECKED} checked labels for: {short}")

    ok(
        f"{len(items)} items, 3 tasks, types {sorted(types)}; test split {len(test)} items, "
        f"hash {digest[:12]}… matches; labels checked per task: {checked}"
    )


if __name__ == "__main__":
    main()
