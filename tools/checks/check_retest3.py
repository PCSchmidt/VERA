"""Gate `judge_retest_3`: the judge re-tested on this increment's claims and loop decisions, within its caps.

It does NOT require a particular agreement: a failure opens T1 or the routing again in the review, it does not block.
Requires:
- data/claim_bench/results.json, from the constructed claim-support benchmark: its test hash equals the one recorded in
  data/claim_bench/split.json, agreement with 95% intervals for the chosen routing and the reference over every
  test item,
  the dev choice between the two routings recorded, and a reference spend within the $1.00 cap;
- data/claim_bench/real_results.json and real_claims_labels.csv: at least 30 real claims labelled (a person or a named,
  disclosed helper), each with a verdict from both routings and the reference, spend within its cap, and the labels'
  provenance stated;
- data/retest3/: items.jsonl with its SHA-256 equal to the one in split.json (recomputed here), results covering exactly
  those items with item-level agreement and intervals for the decided path and the reference, a stated verdict on T1's
  reverse-if 1, the two Increment 2 confident misses examined, the idea_worth_run scores reported, and accounting.json
  giving a disposition to every lit.* and loop.* question id seen, its counts adding up.
"""

from __future__ import annotations

import csv
import hashlib
import json

from _common import block, ok, repo_root_arg

CAP_USD = 1.00
MIN_REAL = 30


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def need_interval(block_: dict, what: str) -> None:
    if "ci95" not in block_ or len(block_["ci95"]) != 2 or not block_.get("n"):
        block(f"{what}: agreement must be item-level with a 95% interval")


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    root = args.root
    cb = root / "data" / "claim_bench"
    results = load(cb / "results.json", "data/claim_bench/results.json (scripts/run_claim_bench.py)")
    split = load(cb / "split.json", "data/claim_bench/split.json")
    if results["test_sha256"] != split["test_sha256"]:
        block("claim_bench results.json was produced on a different test set than the recorded split")
    if results["test_items"] != split["n_test"]:
        block("claim_bench results.json does not cover exactly the test items")
    if results["dev"]["chosen"] not in results["dev"]["arms"]:
        block("claim_bench: the dev choice between the routings is not recorded")
    for who in ("chosen_path", "reference"):
        need_interval(results["test"][who]["agreement"], f"claim_bench {who}")
        if results["test"][who]["agreement"]["n"] != split["n_test"]:
            block(f"claim_bench {who} does not cover every test item")
    if results["spend_usd"]["reference"] > CAP_USD or not (root / results["ledger"]).exists():
        block("claim_bench: reference spend over the cap, or the ledger is missing")

    real = load(cb / "real_results.json", "data/claim_bench/real_results.json (scripts/run_real_claims.py)")
    labels_path = cb / "real_claims_labels.csv"
    if not labels_path.exists():
        block("data/claim_bench/real_claims_labels.csv not found")
    labels = list(csv.DictReader(labels_path.open(encoding="utf-8", newline="")))
    if len(labels) < MIN_REAL or real["n"] != len(labels):
        block(
            f"real claims: {len(labels)} labelled, results cover {real['n']}; at least {MIN_REAL} and equal are needed"
        )
    if any(r["supported"] not in ("yes", "no") or not r["labelled_by"] for r in labels):
        block("real claims: every label needs yes or no and who labelled it")
    for who, r in [*real["paths"].items(), ("reference", real["reference"])]:
        need_interval(r["agreement"], f"real claims {who}")
        if r["agreement"]["n"] != len(labels):
            block(f"real claims {who} does not cover every labelled claim")
    if real["spend_usd"]["reference"] > CAP_USD or not real.get("labels"):
        block("real claims: reference spend over the cap, or the label provenance is not stated")

    rt = root / "data" / "retest3"
    items_path = rt / "items.jsonl"
    rt_split = load(rt / "split.json", "data/retest3/split.json (scripts/retest3.py build)")
    if not items_path.exists():
        block("data/retest3/items.jsonl not found")
    lines = [ln for ln in items_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    digest = hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()
    if digest != rt_split["test_sha256"]:
        block("retest3: the items changed since the hash was recorded")
    rr = load(rt / "results.json", "data/retest3/results.json (scripts/retest3.py run)")
    if rr["test_sha256"] != rt_split["test_sha256"] or rr["items"] != len(lines):
        block("retest3: results.json does not cover exactly the recorded items")
    for who in ("decided_path", "reference"):
        need_interval(rr[who]["agreement"], f"retest3 {who}")
        if rr[who]["agreement"]["n"] != len(lines):
            block(f"retest3 {who} does not cover every item")
    if "fired" not in rr["t1_reverse_if_1"]:
        block("retest3: no verdict on T1's reverse-if 1")
    if {m["id"] for m in rr["increment2_confident_misses"]} != {"retest-0008", "retest-0038"}:
        block("retest3: the two Increment 2 confident misses are not both examined")
    if "score_counts" not in rr["idea_worth_run"]:
        block("retest3: idea_worth_run is not reported")
    if rr["spend_usd"]["reference"] > CAP_USD or not (root / rr["ledger"]).exists():
        block("retest3: reference spend over the cap, or the ledger is missing")
    acc = load(rt / "accounting.json", "data/retest3/accounting.json (scripts/verdict_accounting.py)")
    if sum(v["records"] for v in acc["by_question"].values()) != acc["records"] or not all(
        v["disposition"] for v in acc["by_question"].values()
    ):
        block("accounting: the counts do not add up, or a question id has no disposition")
    d = rr["decided_path"]["agreement"]
    c = results["test"]["chosen_path"]["agreement"]
    ok(
        f"claim benchmark {c['k']}/{c['n']} (chosen {results['dev']['chosen']}); {len(labels)} real claims; "
        f"loop decisions {d['k']}/{d['n']} vs labels; T1 reverse-if 1 fired: {rr['t1_reverse_if_1']['fired']}; "
        f"{acc['records']} verdicts accounted for"
    )


if __name__ == "__main__":
    main()
