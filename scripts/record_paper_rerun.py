# ruff: noqa: E501
"""Record a paper made through the app for the `paper_rerun` gate (Increment 7): copy its evidence into the repo.

    uv run python scripts/record_paper_rerun.py <run_id> --kind remade|new --notes "what changed, what still reads wrong"

As `record_paper_demo.py` (Increment 6), into `data/paper_rerun/<run_id>/`, with the paper's sentence records, the
targeted search's report and any works it added. The passages are not copied. Spend, caps, lights and the kept and
removed counts are never typed here: `tools/checks/check_paper_rerun.py` reads them from the copied files.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FILES = ["app_request.json", "app_state.json", "scope.json", "literature.md", "claims.jsonl", "retrieved.jsonl",
                "sentences.jsonl", "audit.md", "artifacts/audit_report.json"]  # fmt: skip
PAPER_FILES = ["app_paper_request.json", "app_state.json", "request.json", "reading.json", "outline.json", "verify.json",
               "paper.md", "paper.json", "claims.jsonl", "inferences.jsonl", "audit.md", "audit_report.json",
               "coverage.json", "added_records.jsonl"]  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_id")
    ap.add_argument("--kind", choices=["remade", "new"], required=True, help="remade: P2's review again; new: a review not used in Increment 6")
    ap.add_argument("--notes", required=True, help="your own notes on the paper")
    args = ap.parse_args()
    run_dir, out = ROOT / "runs" / args.run_id, ROOT / "data" / "paper_rerun" / args.run_id
    paper = run_dir / "paper"
    if not (paper / "paper.json").exists():
        raise SystemExit(f"{paper} has no finished paper")
    for rel in REVIEW_FILES:
        if (run_dir / rel).exists():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(run_dir / rel, out / rel)
    for rel in PAPER_FILES:
        if (paper / rel).exists():
            (out / "paper").mkdir(parents=True, exist_ok=True)
            shutil.copy(paper / rel, out / "paper" / rel)
    shutil.copy(ROOT / "data" / "ledger" / f"run_{args.run_id}.jsonl", out / "ledger.jsonl")
    who = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=False).stdout.strip()
    record_path = ROOT / "data" / "paper_rerun" / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {"papers": []}
    record["papers"] = [p for p in record["papers"] if p["run_id"] != args.run_id]
    record["papers"].append({"run_id": args.run_id, "kind": args.kind, "notes": args.notes, "notes_by": who or "unknown",
                             "recorded_at": datetime.now(UTC).isoformat(timespec="seconds")})  # fmt: skip
    record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"recorded {args.run_id} ({args.kind}) in data/paper_rerun/ ({len(record['papers'])} papers on record)")


if __name__ == "__main__":
    main()
