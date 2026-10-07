# ruff: noqa: E501
"""Copy a walkthrough run's evidence into data/walkthrough/<run_id>/ (never the key: none of these files holds one).

Takes the run's directory under runs/ and its ledger under data/ledger/: the request, the final state, the review, its claims and
audit, and the ledger. The record of the session itself is data/walkthrough/record.json (template: record.template.json).

Usage: uv run python scripts/collect_walkthrough_run.py <run_id>
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["app_request.json", "app_state.json", "scope.json", "literature.md", "claims.jsonl", "audit.md", "best_so_far.json",
         "gates.jsonl", "retrieved.jsonl"]  # fmt: skip


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    run_id = sys.argv[1]
    src, dest = ROOT / "runs" / run_id, ROOT / "data" / "walkthrough" / run_id
    if not src.exists():
        raise SystemExit(f"no run {run_id!r} under runs/")
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if (src / name).exists():
            shutil.copy(src / name, dest / name)
    report = src / "artifacts" / "audit_report.json"
    if report.exists():
        shutil.copy(report, dest / "audit_report.json")
    shutil.copy(ROOT / "data" / "ledger" / f"run_{run_id}.jsonl", dest / "ledger.jsonl")
    print(f"copied to {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
