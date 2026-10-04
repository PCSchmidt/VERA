# ruff: noqa: E501
"""Gate `audit4_ready` (seeded set): the audit v3 was tested once, on a test split fixed before it ran, with the audit frozen.

Requires data/seeded_v3/ to hold:
- split.json and manifest.csv; the test items' SHA-256 recomputed from the files equals the one recorded in
  split.json (the test set was not edited after the split was fixed);
- at least 24 planted test faults, 6 unmodified test controls, 6 fault types and 4 source documents in test, and no
  document in both dev and test;
- the audit's frozen source hash (split.json) equal to the hash the test run recorded (results_test.json) and to the
  audit's source as it is now (an audit changed after the freeze has not been tested);
- results_test.json with a per-type detection table with confidence intervals, and a spend within the cap ($0.5).
Detection rates are reported, not gated: a low rate is evidence for the review.
"""

from __future__ import annotations

import csv
import hashlib
import json

from _common import block, ok, repo_root_arg

FROZEN_FILES = ["vera/audit/__init__.py", "vera/audit/alignment.py", "vera/audit/bibliography.py",
                "vera/audit/citations.py", "vera/audit/literature.py", "vera/audit/numbers.py",
                "vera/literature/questions.py", "vera/literature/synthesis.py", "vera/literature/reading.py",
                "vera/loop/tables.py", "vera/audit/basis.py", "vera/audit/figure_check.py", "vera/audit/method_code.py",
                "vera/audit/novelty.py", "vera/loop/figures.py"]  # fmt: skip


def source_hash(root) -> str:
    h = hashlib.sha256()
    for rel in sorted(FROZEN_FILES):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def item_files(root, row: dict) -> list:
    base = root / "data" / "seeded_v3"
    d = base / "base" / row["doc"] if row["fault_type"] == "control" else base / "items" / f"{row['doc']}__{row['fault_type']}"
    files = [d / "paper.md", d / "methods.json", d / "figures.json"] if row["kind"] == "paper" else [d / "literature.md", d / "claims.jsonl"]
    return [p for p in files if p.exists()]


def test_hash(root, rows: list[dict]) -> str:
    items = [{**r, "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in item_files(root, r)]} for r in rows]
    lines = sorted(json.dumps(i, sort_keys=True, ensure_ascii=False) for i in items)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=0.5)
    args = parser.parse_args()
    root = args.root
    base = root / "data" / "seeded_v3"
    for name in ("split.json", "manifest.csv", "results_test.json"):
        if not (base / name).exists():
            block(f"data/seeded_v3/{name} not found (scripts/build_seeded_v3.py, scripts/run_seeded_v3.py)")
    split = json.loads((base / "split.json").read_text(encoding="utf-8"))
    manifest = list(csv.DictReader((base / "manifest.csv").open(encoding="utf-8", newline="")))
    test = [r for r in manifest if r["split"] == "test"]
    try:
        recomputed = test_hash(root, test)
    except FileNotFoundError as exc:
        block(f"a test item's file is missing: {exc.filename}")
    if recomputed != split["test_sha256"]:
        block("the test items' hash differs from the one fixed in split.json: the test set was edited")
    faults = [r for r in test if r["fault_type"] != "control"]
    controls = [r for r in test if r["fault_type"] == "control"]
    if len(faults) < 24 or len(controls) < 6:
        block(f"test split has {len(faults)} faults and {len(controls)} controls; needs at least 24 and 6")
    if len({r["fault_type"] for r in faults}) < 6:
        block("test split has fewer than 6 fault types")
    new_types = {"method_code_missing_step", "method_code_undescribed", "figure_altered", "reproduction_basis_wrong"}
    if not new_types <= {r["fault_type"] for r in faults}:
        block(f"the test split lacks the v3 fault types {sorted(new_types - {r['fault_type'] for r in faults})}")
    docs_test = {r["doc"] for r in test}
    if len(docs_test) < 4 or docs_test & {r["doc"] for r in manifest if r["split"] == "dev"}:
        block("test needs at least 4 source documents and none shared with dev")
    frozen = split.get("frozen_audit_sha256")
    results = json.loads((base / "results_test.json").read_text(encoding="utf-8"))
    summary = results["summary"]
    if not frozen:
        block("the audit was never frozen (scripts/freeze_audit_v3.py)")
    if summary.get("audit_sha256") != frozen:
        block("the audit source the test run used is not the frozen one")
    if source_hash(root) != frozen:
        block("the audit's source changed after it was frozen; the recorded test result is for an older audit")
    if not summary.get("by_type") or any("ci95" not in v["red"] for v in summary["by_type"].values()):
        block("results_test.json lacks the per-type detection table with intervals")
    if summary["planted"] != len(faults) or summary["controls"] != len(controls):
        block("results_test.json does not cover exactly the test items")
    if summary["spent_usd"] > args.cap_usd:
        block(f"${summary['spent_usd']:.3f} spent, over the ${args.cap_usd} cap")
    red, flagged = summary["red"], summary["flagged"]
    ok(
        f"test run on {len(faults)} faults and {len(controls)} controls, frozen audit: red {red['k']}/{red['n']}, "
        f"flagged {flagged['k']}/{flagged['n']}, false fails {summary['false_fails']}"
    )


if __name__ == "__main__":
    main()
