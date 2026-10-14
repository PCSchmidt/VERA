# ruff: noqa: E501
"""Re-audit the five papers with the Increment 8 routing and rules (SPEC "The five papers re-audited", gate `reaudit8`).

The papers: Increment 6's P1-P3 and Increment 7's N1, N2. Each is audited as it was made, on a temporary copy of its live
run (`runs/<run>/`, which holds the passages; P2's Increment 6 paper is in `runs/<run>/paper_incr6/` since N1 replaced it),
so no run's own audit is overwritten. The audit now routes each new question by `cheap_path.QUESTION_ROUTES`, has the
reference judge confirm a "no" on the questions in `CONFIRM_NO`, and reports a judge disagreement as a warning (AUD-F-13).

Writes `data/reaudit8/<paper>/audit_report.json` and `audit.md`, and `data/reaudit8/record.json`: for each paper the light
and the failures before (Increment 7's audit) and after, the disagreements, and the backends that answered; who ran it
(`--by`, with `--attribution` when it is not Chris). Judge calls into `data/ledger/reaudit8.jsonl`, capped at $0.50 (raised from the SPEC's $0.25 by Chris, 2026-10-14).

    uv run python scripts/reaudit8.py --by "Chris"
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.app import pipeline  # noqa: E402
from vera.judge.cheap_path import QUESTION_ROUTES, cheap_path, confirmer  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.literature.deps import LitDeps  # noqa: E402
from vera.schemas import Budget, RunRequest  # noqa: E402

CAP_USD = 0.50  # raised from the SPEC's $0.25 by Chris (2026-10-14): the reference confirms about 76 "no" verdicts
OUT = ROOT / "data" / "reaudit8"
# paper -> (live run, the paper's folder in it, Increment 7's audit report of it)
PAPERS = {
    "P1": ("how-much-useable-information-about-6x3n", "paper", "data/paper_rerun/reaudit/how-much-useable-information-about-6x3n/audit_report.json"),
    "P2": ("discuss-the-evolution-of-prompting-guv8", "paper_incr6", "data/paper_rerun/reaudit/discuss-the-evolution-of-prompting-guv8/audit_report.json"),
    "P3": ("rlm-vs-clm-3", "paper", "data/paper_rerun/reaudit/rlm-vs-clm-3/audit_report.json"),
    "N1": ("discuss-the-evolution-of-prompting-guv8", "paper", "data/paper_rerun/discuss-the-evolution-of-prompting-guv8/paper/audit_report.json"),
    "N2": ("rlm-vs-clm-2", "paper", "data/paper_rerun/rlm-vs-clm-2/paper/audit_report.json"),
}


def tally(report: dict) -> dict:
    fails = Counter(f["check"] for f in report["findings"] if f["severity"] == "fail")
    disagree = sum(1 for f in report["findings"] if f["summary"].startswith("judges disagree"))
    return {"light": report["overall"], "fails": dict(fails), "disagreements": disagree,
            "warns": sum(1 for f in report["findings"] if f["severity"] == "warn")}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--by", required=True)
    ap.add_argument("--attribution", default="")
    args = ap.parse_args()
    if args.by != "Chris" and not args.attribution.strip():
        sys.exit("--attribution is required when it is not Chris who runs it")
    ledger_path = ROOT / "data" / "ledger" / "reaudit8.jsonl"
    earlier = sum(r.cost_usd for r in Ledger(ledger_path).records()) if ledger_path.exists() else 0.0
    if earlier >= CAP_USD:
        sys.exit(f"the re-audit cap (${CAP_USD:.2f}) is spent")
    ledger = Ledger(ledger_path, run_id="reaudit8")
    budget = Budget(max_usd=CAP_USD - earlier, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="p2.reaudit8")
    reference = confirmer(ledger=ledger, budget=budget, component="p2.reaudit8.confirm")
    record = {"run_by": args.by, "attribution": args.attribution.strip() or None,
              "routes": {k: list(v) for k, v in QUESTION_ROUTES.items()}, "papers": {}}  # fmt: skip
    for label, (run_id, folder, before_path) in PAPERS.items():
        live = ROOT / "runs" / run_id
        if not (live / folder / "passages.jsonl").exists():
            sys.exit(f"{live / folder}/passages.jsonl not found: the re-audit needs the live run")
        before = json.loads((ROOT / before_path).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / run_id
            shutil.copytree(live, run_dir, ignore=shutil.ignore_patterns("checkpoints.sqlite*", "worker.log", "paper", "paper_incr6"))
            shutil.copytree(live / folder, run_dir / "paper")
            request = RunRequest.model_validate(json.loads((live / "app_request.json").read_text(encoding="utf-8")))
            deps = LitDeps(spec=pipeline.make_spec(request), generator=None, judge=judge, budget=budget, run_dir=run_dir, ledger=ledger)
            pipeline.run_paper_audit(deps, judge=judge, reference=reference)
            dest = OUT / label
            dest.mkdir(parents=True, exist_ok=True)
            for name in ("audit_report.json", "audit.md"):
                shutil.copy(run_dir / "paper" / name, dest / name)
        after = json.loads((dest / "audit_report.json").read_text(encoding="utf-8"))
        backends = Counter(v["backend"] for f in after["findings"] for v in f.get("verdicts", []))
        record["papers"][label] = {"run": run_id, "folder": folder, "before": tally(before), "after": tally(after),
                                   "backends_in_findings": dict(backends)}  # fmt: skip
        print(f"{label}: {record['papers'][label]['before']['light']} -> {after['overall']}; after {tally(after)}")
    record["spend_usd"] = round(sum(r.cost_usd for r in Ledger(ledger_path).records()), 4)
    record["recorded_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT / "record.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"spend ${record['spend_usd']:.4f} of ${CAP_USD:.2f}")


if __name__ == "__main__":
    main()
