"""Gate `audit_ready`: the audit's seeded-fault evidence is complete, honest and unchanged (docs/06 §1, §5).

Requires:
- data/seeded/manifest.csv, split.json and the planted papers; every fault type has at least 3 test items and the
  test split has at least 3 controls (unmodified papers);
- dev and test are split by base paper (disjoint);
- the test items' SHA-256 recomputed now equals the one recorded when the split was fixed (the test set did not change
  after the audit was developed against dev);
- data/seeded/results_dev.json was produced before results_test.json (the audit was developed on dev first);
- results_test.json covers exactly the current test items, with red detection (at least one `fail`) >= 90% of planted
  faults overall (the SPEC's bar, AUD-P-01's starting value, not yet a target), every fault type flagged (amber or red)
  at >= 90%, and no `fail` on any control (a `warn` on a control is reported: an unverifiable design number is amber);
- the live runs' ledgers exist and their spend is within $0.50 each.
"""

from __future__ import annotations

import csv
import hashlib
import json

from _common import block, ok, repo_root_arg

FAULT_TYPES = ["fabricated_citation", "unretrieved_citation", "altered_reference", "numeric_prose", "numeric_table",
               "fabricated_claim"]  # fmt: skip
BAR = 0.90
CAP_USD = 0.50


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    seeded = args.root / "data" / "seeded"
    for name in ("manifest.csv", "split.json", "results_dev.json", "results_test.json"):
        if not (seeded / name).exists():
            block(f"data/seeded/{name} not found (scripts/build_seeded_faults.py, scripts/run_seeded_audit.py)")
    with (seeded / "manifest.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    split = json.loads((seeded / "split.json").read_text(encoding="utf-8"))

    test = [r for r in rows if r["split"] == "test"]
    types = [r["fault_type"] for r in test]
    if types.count("control") < 3:
        block("the test split needs at least 3 controls")
    for kind in FAULT_TYPES:
        if types.count(kind) < 3:
            block(f"the test split has {types.count(kind)} {kind} items; at least 3 are needed")
    if set(split["dev_bases"]) & set(split["test_bases"]):
        block("dev and test share a base paper")

    items = []
    for r in test:
        path = (seeded / "base" / r["paper_id"] / "paper.md") if r["fault_type"] == "control" else (
            seeded / "papers" / f"{r['fault_id'].replace(':', '__')}.md")  # fmt: skip
        items.append({**r, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    digest = hashlib.sha256(
        "\n".join(sorted(json.dumps(i, sort_keys=True, ensure_ascii=False) for i in items)).encode("utf-8")
    ).hexdigest()
    if digest != split["test_sha256"]:
        block("the test items changed since the split was fixed (hash mismatch)")

    if (seeded / "results_dev.json").stat().st_mtime >= (seeded / "results_test.json").stat().st_mtime:
        block("results_dev.json is not older than results_test.json: develop on dev, then run the test split")
    result = json.loads((seeded / "results_test.json").read_text(encoding="utf-8"))
    if {i["fault_id"] for i in result["items"]} != {r["fault_id"] for r in test}:
        block("results_test.json does not cover exactly the current test items; rerun scripts/run_seeded_audit.py")
    summary = result["summary"]
    if summary["controls"] < 3 or summary["false_fails"] > 0:
        block(f"{summary['false_fails']} of {summary['controls']} unmodified controls raised a fail")
    if summary["detection_rate"] < BAR:
        block(f"detection {summary['detection_rate']:.0%} is below {BAR:.0%}")
    for kind, c in summary["by_type"].items():  # per type: flagged (amber or red); red detection is gated overall
        if c["n"] and c["flagged"] < BAR * c["n"]:
            block(f"{kind}: {c['flagged']} of {c['n']} flagged, below {BAR:.0%}")
    for name in ("results_dev.json", "results_test.json"):
        s = json.loads((seeded / name).read_text(encoding="utf-8"))["summary"]
        if not (args.root / s["ledger"]).exists() or s["spent_usd"] > CAP_USD:
            block(f"{name}: ledger {s['ledger']} missing or spend ${s['spent_usd']} over ${CAP_USD}")
    ok(
        f"seeded audit: test detection {summary['detection_rate']:.0%} ({summary['detected']}/{summary['planted']}), "
        f"{summary['false_fails']} false fails on {summary['controls']} controls, test hash unchanged"
    )


if __name__ == "__main__":
    main()
