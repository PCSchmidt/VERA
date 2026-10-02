"""Gate `judge_retest`: the judge was re-tested on the loop's real gate decisions, honestly and within its cap.

Requires (it does NOT require a particular agreement: a failure opens T1 again in the review rather than blocking):
- data/retest/items.jsonl with at least 100 items, a recorded split (split.json) and the test items' SHA-256 unchanged
  since the split was fixed (recomputed here);
- the coverage count in split.json accounts for every loop.* record seen: records = excluded (no shadow answer or
  older wording) + merged duplicates + distinct real items;
- data/retest/results.json covers exactly the test items, with item-level agreement and 95% intervals for both the
  decided path and the reference, and a stated verdict on T1's reverse-if 1;
- the re-test's ledger exists and its reference spend is within the $1.00 cap.
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg

MIN_ITEMS = 100
CAP_USD = 1.00


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    retest = args.root / "data" / "retest"
    for name in ("items.jsonl", "split.json", "results.json"):
        if not (retest / name).exists():
            block(f"data/retest/{name} not found (scripts/build_retest.py, scripts/run_retest.py)")
    lines = [ln for ln in (retest / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    items = [json.loads(ln) for ln in lines]
    split = json.loads((retest / "split.json").read_text(encoding="utf-8"))
    if len(items) < MIN_ITEMS:
        block(f"{len(items)} items; at least {MIN_ITEMS} are needed")
    test = [json.loads(ln) for ln in lines if json.loads(ln)["split"] == "test"]
    if not test or not [i for i in items if i["split"] == "dev"]:
        block("both a dev and a test split are needed")
    test_lines = [ln for ln in lines if json.loads(ln)["split"] == "test"]
    digest = hashlib.sha256("\n".join(sorted(test_lines)).encode("utf-8")).hexdigest()
    if digest != split["test_sha256"]:
        block("the test items changed since the split was fixed (hash mismatch)")
    cov = split["coverage"]
    accounted = (
        cov["excluded_no_shadow_answer"]
        + cov.get("excluded_older_question_wording", 0)
        + cov["duplicates_merged"]
        + cov["distinct_real_items"]
    )
    if accounted != cov["records"]:
        block(f"coverage does not add up: {accounted} accounted of {cov['records']} loop.* records")
    results = json.loads((retest / "results.json").read_text(encoding="utf-8"))
    if results["test_sha256"] != split["test_sha256"]:
        block("results.json was produced on a different test set than the recorded split")
    if results["test_items"] != len(test):
        block("results.json does not cover exactly the test items")
    for who in (
        results["decided_path"]["agreement_with_label_item_level"],
        results["reference"]["agreement_with_label_item_level"],
    ):
        if who["n"] != len(test) or len(who["ci95"]) != 2:
            block("agreement must be item-level over every test item, with a 95% interval")
    verdict = results["t1_reverse_if_1"]
    if "fired" not in verdict:
        block("results.json states no verdict on T1's reverse-if 1")
    if results["spend_usd"]["reference"] > CAP_USD:
        block(f"reference spend ${results['spend_usd']['reference']:.4f} exceeds the ${CAP_USD:.2f} cap")
    if not (args.root / results["ledger"]).exists():
        block("the re-test ledger is missing")
    d = results["decided_path"]["agreement_with_label_item_level"]
    ok(
        f"judge re-test: {len(items)} items ({len(test)} test); decided path {d['k']}/{d['n']} = {d['rate']:.1%} "
        f"(95% CI {d['ci95'][0]:.1%}-{d['ci95'][1]:.1%}); T1 reverse-if 1 fired: {verdict['fired']}; "
        "test hash unchanged"
    )


if __name__ == "__main__":
    main()
