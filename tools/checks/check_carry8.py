# ruff: noqa: E501
"""Increment 8 checks, by part (SPEC.md). Exit 0 passes, exit 2 blocks.

--part set       (gate `judge_set_frozen`): the judge set has the SPEC's counts per question (about 120, 80, 80), is split
                 by paper (dev P1, N1; test P2, P3, N2), JDG-P-04 tests rebuild items with the pipeline's own question
                 functions, the freeze (test items and measuring code) is written and still matches the set, and no
                 test result predates it. Earlier freezes hold (Increment 5 audit files, Increment 6 inference files,
                 Increment 7 real-case files).

--part measured  (gate `judge_measured`): the one test run came after the freeze, on the frozen test items and measuring
                 code; it reports, for every question and backend, agreement with the reference with its interval, flip
                 rate, share below the threshold, ECE, cost and latency, and whether the bars are met; the labelled
                 sample was recorded before the run and its post-hoc reading exists; spend within the $3 cap.

--part routing   (gate `routing_ready`): the route table covers the three measured questions and is used by the cheap path
                 (so the write step and the audit share it); the audit confirms a "no" on the chosen questions with the
                 reference judge; the disagreement rule is applied by both audits; interpretation statements store
                 their write-time verdicts; JDG-F-07 and AUD-F-13 tests exist; the earlier freezes hold.

Later parts (reaudit) are added with their features.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _common import block, ok, repo_root_arg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_carry6 import frozen_unchanged, has_tests  # noqa: E402
from check_carry7 import inference_hash_holds  # noqa: E402

RANGES = {"within_quote": (100, 140), "no_fact": (60, 100), "inference": (70, 100)}


def realcase_hash_holds(root: Path) -> str:
    sys.path.insert(0, str(root / "scripts"))
    import measure_realcase as mr  # noqa: PLC0415

    frozen = json.loads((root / "data" / "results" / "realcase_hash_incr7.json").read_text(encoding="utf-8"))
    if frozen["check_sha256"] != mr.check_hashes():
        block("a file hashed for Increment 7's real-case measurement changed (sentence_checks.py, audit/sentences.py, ...)")
    return "real-case files unchanged"


def part_set(root: Path) -> None:
    sys.path.insert(0, str(root / "scripts"))
    import measure_judge8 as mj  # noqa: PLC0415

    path = root / "data" / "judge8" / "items.jsonl"
    if not path.exists():
        block("data/judge8/items.jsonl not found (scripts/build_judge_set8.py)")
    items = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for kind, (lo, hi) in RANGES.items():
        n = sum(1 for i in items if i["kind"] == kind)
        if not lo <= n <= hi:
            block(f"{kind}: {n} items, outside the SPEC's range {lo}-{hi}")
    split = {i["paper"]: i["split"] for i in items}
    if split != {"P1": "dev", "N1": "dev", "P2": "test", "P3": "test", "N2": "test"}:
        block(f"the split is not by paper as the SPEC says: {split}")
    freeze = root / "data" / "results" / "judge8_hash.json"
    if not freeze.exists():
        block("no freeze (scripts/measure_judge8.py freeze)")
    frozen = json.loads(freeze.read_text(encoding="utf-8"))
    if frozen["test_sha256"] != mj.test_hash():
        block("the test items changed after the freeze")
    result = root / "data" / "results" / "judge8_test.json"
    if result.exists() and json.loads(result.read_text(encoding="utf-8"))["run_at"] <= frozen["frozen_at"]:
        block("a test result predates the freeze")
    n = has_tests(root, "JDG-P-04", 2)
    counts = {k: sum(1 for i in items if i["kind"] == k) for k in RANGES}
    ok(f"judge set {counts}, split by paper, frozen {frozen['frozen_at']}; {n} JDG-P-04 tests; audit files unchanged ({frozen_unchanged(root)}); "
       f"{inference_hash_holds(root)}; {realcase_hash_holds(root)}")


def part_measured(root: Path) -> None:
    sys.path.insert(0, str(root / "scripts"))
    import measure_judge8 as mj  # noqa: PLC0415

    from vera.ledger import Ledger  # noqa: PLC0415

    results = root / "data" / "results"
    frozen = json.loads((results / "judge8_hash.json").read_text(encoding="utf-8"))
    path = results / "judge8_test.json"
    if not path.exists():
        block("no test result (scripts/measure_judge8.py test)")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["run_at"] <= frozen["frozen_at"] or result["test_sha256"] != frozen["test_sha256"] or result["check_sha256"] != frozen["check_sha256"]:
        block("the test result does not come after the freeze, on the frozen set and code")
    if frozen["test_sha256"] != mj.test_hash():
        block("the test items changed after the freeze")
    for kind in mj.KINDS:
        row = result["summary"].get(kind) or {}
        for name in ("jev", "glm", "decided", "reference"):
            r = row.get(name) or {}
            for key in ("agreement_with_reference", "flip_rate", "below_threshold", "ece_vs_reference", "cost_per_verdict_usd", "latency_p50_ms"):
                if key not in r:
                    block(f"{kind} {name}: no {key}")
            if name != "reference" and "meets_bars" not in r:
                block(f"{kind} {name}: not judged against the bars")
        if "route" not in row:
            block(f"{kind}: no route reading")
    labels = root / "data" / "judge8" / "labels.json"
    if labels.exists() and json.loads(labels.read_text(encoding="utf-8"))["labelled_at"] >= result["run_at"]:
        block("the labelled sample was recorded after the test run, so it is not blind")
    if labels.exists() and not (results / "judge8_test_posthoc.json").exists():
        block("no post-hoc reading of the labelled sample (scripts/judge8_posthoc.py)")
    spend = sum(sum(r.cost_usd for r in Ledger(p).records()) for p in (root / "data" / "ledger").glob("judge8_*.jsonl"))
    if spend > mj.CAP_USD:
        block(f"spend ${spend:.4f} is over the ${mj.CAP_USD:.2f} cap")
    met = {k: [n for n in ("jev", "glm", "decided") if result["summary"][k][n]["meets_bars"]] for k in mj.KINDS}
    ok(f"measured after the freeze ({frozen['frozen_at']}); backends meeting both bars: {met}; spend ${spend:.4f} of ${mj.CAP_USD:.2f}")


def part_routing(root: Path) -> None:
    from vera.judge import cheap_path as cp  # noqa: PLC0415

    want = {"claim.within_quote", "sentence.no_fact", "paper.inference_follows"}
    if set(cp.QUESTION_ROUTES) != want:
        block(f"the route table covers {sorted(cp.QUESTION_ROUTES)}, not the three measured questions")
    if not set(cp.CONFIRM_NO) <= want or not cp.CONFIRM_NO:
        block("no question is confirmed with the reference, or one outside the measured three")
    text = (root / "vera" / "judge" / "cheap_path.py").read_text(encoding="utf-8")
    if "routes=routes" not in text or "def router_for(" not in text:
        block("the cheap path does not route by the table")
    pipeline = (root / "vera" / "app" / "pipeline.py").read_text(encoding="utf-8")
    for needed in ("disagreement.reconcile(", "CONFIRM_NO", "confirmations=confirmations"):
        if pipeline.count(needed) < 1:
            block(f"the app pipeline lacks {needed}")
    if pipeline.count("confirmations=confirmations") < 2:
        block("both audits (review and paper) must confirm and reconcile")
    if "verdicts=per.get(" not in (root / "vera" / "literature" / "paper_interpret.py").read_text(encoding="utf-8"):
        block("interpretation statements do not store their write-time verdicts")
    n7 = has_tests(root, "JDG-F-07", 3)
    n13 = has_tests(root, "AUD-F-13", 5)
    ok(f"routes for {sorted(want)}; confirm {sorted(cp.CONFIRM_NO)} with the reference; disagreement rule in both audits; "
       f"{n7} JDG-F-07 and {n13} AUD-F-13 tests; audit files unchanged ({frozen_unchanged(root)}); {inference_hash_holds(root)}; "
       f"{realcase_hash_holds(root)}")


PARTS = {"set": part_set, "measured": part_measured, "routing": part_routing}


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--part", choices=sorted(PARTS), required=True)
    args = parser.parse_args()
    PARTS[args.part](args.root)


if __name__ == "__main__":
    main()
