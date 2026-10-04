"""Run the v3 audit over the seeded-fault set v3 (Increment 4), live: the real judge path and bibliographic sources.

  --split dev     free to repeat: the audit is developed against dev only
  --freeze        records the audit's own source hash in data/seeded_v3/split.json (once), before the test run
  --split test    verifies the test items' hash and that the audit's source is exactly what was frozen, refuses
                  to run if results_test.json already exists (a test set is spent by one run), and records the
                  audit hash it ran

Writes data/seeded_v3/results_<split>.json (per item, and per fault type with Wilson intervals) and a
never-overwritten ledger data/ledger/run_seededv3-<split>-<n>.jsonl. Detected = at least one `fail` finding on a
planted fault; a `fail` on an unmodified control is a false positive.

Usage: uv run python scripts/run_seeded_v3.py --split dev
       uv run python scripts/run_seeded_v3.py --freeze
       uv run python scripts/run_seeded_v3.py --split test
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from vera.audit import seeded_v3
from vera.audit.bibliography import SourceLookup
from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "data" / "seeded_v3"
TARGET = ROOT / "docs" / "results" / "treehfd_baseline_target.json"
MIN_CONFIDENCE = 0.7


def build_script():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_seeded_v3  # noqa: PLC0415

    return build_seeded_v3


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def summarise(rows: list[dict], manifest: dict[str, dict]) -> dict:
    planted = [r for r in rows if r["fault_type"] != "control"]
    controls = [r for r in rows if r["fault_type"] == "control"]
    by_type = {}
    for t in sorted({r["fault_type"] for r in planted}):
        sel = [r for r in planted if r["fault_type"] == t]
        by_type[t] = {"red": rate(sum(r["detected"] for r in sel), len(sel)),
                      "flagged": rate(sum(r["detected"] or r["n_warn"] > 0 for r in sel), len(sel)),
                      "subtle": t in seeded_v3.SUBTLE}  # fmt: skip
    subtle = [r for r in planted if r["fault_type"] in seeded_v3.SUBTLE]
    plain = [r for r in planted if r["fault_type"] not in seeded_v3.SUBTLE]
    return {
        "planted": len(planted), "red": rate(sum(r["detected"] for r in planted), len(planted)),
        "flagged": rate(sum(r["detected"] or r["n_warn"] > 0 for r in planted), len(planted)),
        "subtle_red": rate(sum(r["detected"] for r in subtle), len(subtle)),
        "deterministic_red": rate(sum(r["detected"] for r in plain), len(plain)),
        "controls": len(controls), "false_fails": sum(r["detected"] for r in controls),
        "controls_flagged": sum(r["detected"] or r["n_warn"] > 0 for r in controls),
        "controls_with_method_code_warns": sum(r["n_method_code_warns"] > 0 for r in controls),
        "by_type": by_type,
        "by_doc_kind": {k: rate(sum(r["detected"] for r in planted if manifest[r["fault_id"]]["kind"] == k),
                                sum(manifest[r["fault_id"]]["kind"] == k for r in planted)) for k in ("paper", "lit")},
    }  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test"])
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--max-usd", type=float, default=0.5)
    args = ap.parse_args()
    split_file = V3 / "split.json"
    split = json.loads(split_file.read_text(encoding="utf-8"))
    audit_hash = seeded_v3.audit_source_sha256(ROOT)
    if args.freeze:
        if split["frozen_audit_sha256"]:
            raise SystemExit(f"already frozen at {split['frozen_at']}: {split['frozen_audit_sha256'][:12]}")
        stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        split |= {"frozen_audit_sha256": audit_hash, "frozen_at": stamp}
        split_file.write_text(json.dumps(split, indent=1), encoding="utf-8")
        print(f"audit frozen: {audit_hash[:16]} (the test run needs exactly this source)")
        return
    if not args.split:
        raise SystemExit("give --split dev, --split test or --freeze")
    manifest = list(csv.DictReader((V3 / "manifest.csv").open(encoding="utf-8", newline="")))
    out = V3 / f"results_{args.split}.json"
    rows_in = [r for r in manifest if r["split"] == args.split]
    if args.split == "test":
        if out.exists():
            raise SystemExit("results_test.json exists: a test set is spent by one run; build a new set to test again")
        if not split["frozen_audit_sha256"]:
            raise SystemExit("freeze the audit first: scripts/run_seeded_v3.py --freeze")
        if split["frozen_audit_sha256"] != audit_hash:
            raise SystemExit("the audit's source changed since it was frozen: this test set can no longer be used")
        if build_script().test_hash([r for r in manifest if r["split"] == "test"]) != split["test_sha256"]:
            raise SystemExit("the test items changed since the split was fixed")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_seededv3-{args.split}-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"seededv3-{args.split}-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=args.max_usd, max_wall_seconds=7200)
    judge = cheap_path(ledger=ledger, budget=budget)
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    lookup = SourceLookup()
    results = []
    for row in rows_in:
        producer = "p3.write_up" if row["kind"] == "paper" else "p3.synthesize"

        def ask(question, material, producer=producer):
            (verdict,) = judge.ask(material, [question])
            verdict = verdict.model_copy(update={"producer_id": producer})
            return verdict, verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE

        run = seeded_v3.audit_item(ROOT, row, ask=ask, lookup=lookup, target=target)
        fails = [f for f in run.report.findings if f.severity == "fail"]
        code_warns = [f for f in run.report.findings if f.check == "method_code"]
        # a method-code finding is a warn by design: for a method-code fault it is what counts as caught
        caught = bool(fails) or (row["fault_type"] in seeded_v3.METHOD_FAULTS and bool(code_warns))
        results.append({"fault_id": row["fault_id"], "fault_type": row["fault_type"], "detected": caught,
                        "n_method_code_warns": len(code_warns), "checks_run": run.report.checks_run,
                        "overall": run.report.overall, "n_fail": len(fails),
                        "n_warn": sum(f.severity == "warn" for f in run.report.findings),
                        "first_fail": fails[0].summary[:240] if fails else None,
                        "cost_usd": run.report.total_cost_usd})  # fmt: skip
    by_id = {r["fault_id"]: r for r in manifest}
    summary = summarise(results, by_id) | {"spent_usd": budget.spent_usd, "audit_sha256": audit_hash,
                                          "ledger": ledger.path.relative_to(ROOT).as_posix()}  # fmt: skip
    out.write_text(json.dumps({"split": args.split, "summary": summary, "items": results}, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_type"}, indent=1))
    for t, v in summary["by_type"].items():
        print(f"  {t:24} red {v['red']['k']}/{v['red']['n']}  flagged {v['flagged']['k']}/{v['flagged']['n']}"
              f"{'  (subtle)' if v['subtle'] else ''}")  # fmt: skip
    for r in results:
        if (r["fault_type"] == "control") == r["detected"]:
            print(f"  {'FALSE FAIL' if r['fault_type'] == 'control' else 'MISS      '} {r['fault_id']} "
                  f"overall={r['overall']} first_fail={r['first_fail']}")  # fmt: skip


if __name__ == "__main__":
    main()
