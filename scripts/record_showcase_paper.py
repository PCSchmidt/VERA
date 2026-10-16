# ruff: noqa: E501
"""Copy a review paper made through the app into `data/papers_showcase/<run_id>/`, for the Pages showcase (no model call).

    uv run python scripts/record_showcase_paper.py <run_id>

As `record_papers9.py`: the paper's files (not its passages), the review's retrieved records the paper's sources are
looked up in, and the run's ledger (the review's and the paper's calls, so `spend_total.py` counts them). The paper's
spend is the ledger's records beyond `spent_before_usd` in `app_paper_request.json`; it is printed for `showcase.json`,
never typed. Made 2026-10-16, after the close, at Chris's request.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_FILES = ["app_paper_request.json", "app_state.json", "request.json", "reading.json", "outline.json", "verify.json",
               "paper.md", "paper.json", "claims.jsonl", "inferences.jsonl", "audit.md", "audit_report.json",
               "coverage.json", "added_records.jsonl"]  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    args = ap.parse_args()
    run_dir, out = ROOT / "runs" / args.run_id, ROOT / "data" / "papers_showcase" / args.run_id
    paper = run_dir / "paper"
    state = json.loads((paper / "app_state.json").read_text(encoding="utf-8")).get("state")
    if state != "complete" or not (paper / "audit_report.json").exists():
        raise SystemExit(f"{paper} has no finished, audited paper (state {state})")
    (out / "paper").mkdir(parents=True, exist_ok=True)
    for rel in PAPER_FILES:
        if (paper / rel).exists():
            shutil.copy(paper / rel, out / "paper" / rel)
    shutil.copy(run_dir / "retrieved.jsonl", out / "retrieved.jsonl")
    ledger = ROOT / "data" / "ledger" / f"run_{args.run_id}.jsonl"
    shutil.copy(ledger, out / "ledger.jsonl")
    total = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip())
    before = json.loads((paper / "app_paper_request.json").read_text(encoding="utf-8"))["spent_before_usd"]
    light = json.loads((paper / "audit_report.json").read_text(encoding="utf-8"))["overall"]
    print(json.dumps({"run_id": args.run_id, "light": light, "paper_spent_usd": round(total - before, 4), "out": out.relative_to(ROOT).as_posix()}))


if __name__ == "__main__":
    main()
