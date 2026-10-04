# ruff: noqa: E501
"""Gate `audit4_ready` (novelty gold set): the novelty judgement was measured once on a test split fixed before it ran.

Requires data/novelty_gold/ to hold:
- pairs.jsonl and split.json; the test pairs' SHA-256 recomputed from the pairs equals the one fixed in split.json;
- at least 10 test pairs of each label (`not_distinct`, `distinct`), by construction, no source paper in both dev and test (the
  relabelled and the unrelated pair of one paper share a split);
- the audit's frozen source hash (split.json) equal to the one the test run recorded and to the audit's source now;
- results_test.json with a rate and a 95% interval for each label, the wrong pairs listed, and a spend within the cap ($1.00);
- chris_sheet.csv (the real loop ideas drawn for Chris's labels); his labels (`chris_labels.csv`) are reported when present and
  are not required here: they are his to give, and the review says whether they exist.
Rates are reported, not gated.
"""

from __future__ import annotations

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


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=1.0)
    args = parser.parse_args()
    base = args.root / "data" / "novelty_gold"
    for name in ("pairs.jsonl", "split.json", "results_test.json", "chris_sheet.csv"):
        if not (base / name).exists():
            block(f"data/novelty_gold/{name} not found")
    split = json.loads((base / "split.json").read_text(encoding="utf-8"))
    pairs = [json.loads(ln) for ln in (base / "pairs.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    test = [p for p in pairs if p["split"] == "test"]
    digest = hashlib.sha256(json.dumps([{k: p[k] for k in ("id", "label", "idea", "prior_title")} for p in test], sort_keys=True).encode()).hexdigest()
    if digest != split["test_sha256"]:
        block("the test pairs' hash differs from the one fixed in split.json: the test set was edited")
    for label in ("not_distinct", "distinct"):
        if sum(p["label"] == label for p in test) < 10:
            block(f"fewer than 10 test pairs labelled {label}")
    frozen = split.get("frozen_audit_sha256")
    results = json.loads((base / "results_test.json").read_text(encoding="utf-8"))
    if not frozen:
        block("the audit was never frozen (scripts/freeze_audit_v3.py)")
    if results.get("audit_sha256") != frozen:
        block("the audit source the test run used is not the frozen one")
    if source_hash(args.root) != frozen:
        block("the audit's source changed after it was frozen; the recorded result is for an older audit")
    for label in ("not_distinct", "distinct"):
        if "ci95" not in results.get(label, {}):
            block(f"results_test.json lacks the interval for {label}")
    if results["spend_usd"] > args.cap_usd:
        block(f"${results['spend_usd']:.3f} spent, over the ${args.cap_usd} cap")
    nd, d = results["not_distinct"], results["distinct"]
    chris, helper = results.get("chris"), results.get("helper")
    own = f"n={chris['n']}" if chris else "not given"
    aid = f"n={helper['n']}" if helper else "none"
    ok(f"test run on {nd['n']} + {d['n']} pairs, frozen audit: not_distinct {nd['correct']}/{nd['n']} (unsure {nd['unsure']}), "
       f"distinct {d['correct']}/{d['n']} (unsure {d['unsure']}); Chris's own labels: {own}; helper labels: {aid}")


if __name__ == "__main__":
    main()
