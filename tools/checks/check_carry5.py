# ruff: noqa: E501
"""Gate `carry5_ready`: the Increment 5 carry-ins are built and measured.

Requires:
- the degenerate-spread rule (`vera/loop/spread.py`) and a test with a planted near-zero spread;
- the larger-N judge re-test (T1 reverse-if (1)): `data/retest5/results.json` over at least 150 items, the items' hash equal to the
  one recorded before any backend ran, the decided path's agreement with the reference stated with its interval, and the run's ledger
  equal to the spend recorded;
- the second keyed source's recall table (`docs/results/retrieval_recall_s2.md`) with the old and new figures pooled and each topic's
  hits committed (a null result is a result);
- the audit's frozen files unchanged since Increment 5 was scoped (`data/results/audit_hash_incr5.json`), because changing one spends
  the audit v3 test sets (SPEC, method-code decision);
- spend: the judge re-test, whose ledger is read here, within the SPEC's $1.50 cap for this item.
"""

from __future__ import annotations

import hashlib
import json

from _common import block, ok, repo_root_arg

MIN_ITEMS = 150
TOPICS = ("research-agents-eval", "conformal-shift", "tabular-trees-vs-nets", "tree-explain", "credal-dro", "llm-judge-numbers")
CAP_USD = 1.5


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    root = args.root
    spread = root / "vera" / "loop" / "spread.py"
    tests = root / "tests" / "test_loop_spread.py"
    if not spread.exists() or "def test_a_planted_near_zero_spread" not in (tests.read_text(encoding="utf-8") if tests.exists() else ""):
        block("the degenerate-spread rule or its planted-spread test is missing")

    results_file, split_file = root / "data" / "retest5" / "results.json", root / "data" / "retest5" / "split.json"
    if not results_file.exists() or not split_file.exists():
        block("data/retest5/results.json (scripts/retest5.py run) or split.json not found")
    results, split = json.loads(results_file.read_text(encoding="utf-8")), json.loads(split_file.read_text(encoding="utf-8"))
    if results["items"] < MIN_ITEMS or split["items"] < MIN_ITEMS:
        block(f"the judge re-test has {results['items']} items; at least {MIN_ITEMS} are required")
    if results["test_sha256"] != split["test_sha256"]:
        block("the results carry a different items hash from the one recorded before any backend ran")
    n_items = len([ln for ln in (root / "data" / "retest5" / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()])
    if n_items != split["items"]:
        block(f"items.jsonl has {n_items} items, the split file records {split['items']}")
    agree = results["decided_path"]["agreement_with_reference"]
    if agree.get("n", 0) < MIN_ITEMS or not agree.get("ci95"):
        block("the decided path's agreement with the reference is missing its count or interval")
    ledger = root / results["ledger"]
    if not ledger.exists():
        block(f"ledger {results['ledger']} not found")
    spent = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip())
    recorded = sum(results["spend_usd"].values())
    if abs(spent - recorded) > 1e-6:
        block(f"ledger total {spent:.6f} differs from the recorded spend {recorded:.6f}")
    if spent > CAP_USD:
        block(f"the judge re-test spent ${spent:.2f}, over its ${CAP_USD:.2f} cap")

    table = root / "docs" / "results" / "retrieval_recall_s2.md"
    if not table.exists():
        block("docs/results/retrieval_recall_s2.md not found (scripts/measure_retrieval5.py)")
    text = table.read_text(encoding="utf-8")
    if "Pooled" not in text or "Found before" not in text or "Found with Semantic Scholar" not in text:
        block("the second-source table lacks the pooled row or the before/after columns")
    for topic in TOPICS:
        if topic not in text or not (root / "data" / "retrieval_s2" / topic / "s2_hits.jsonl").exists():
            block(f"second-source result for {topic} missing from the table or its hits not committed")

    frozen = json.loads((root / "data" / "results" / "audit_hash_incr5.json").read_text(encoding="utf-8"))
    h = hashlib.sha256()
    for rel in sorted(frozen["files"]):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    if h.hexdigest() != frozen["sha256"]:
        block("an audit file frozen at Increment 5's scoping has changed: that spends the audit v3 test sets; decide that first (SPEC)")

    ok(f"spread rule and test present; judge re-test {results['items']} items, decided path vs reference "
       f"{agree['k']}/{agree['n']} ({agree['ci95'][0]:.1%}-{agree['ci95'][1]:.1%}), ${spent:.3f}; second-source table with all six topics; "
       f"audit files unchanged ({frozen['sha256'][:12]})")


if __name__ == "__main__":
    main()
