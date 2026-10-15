# ruff: noqa: E501
"""Record a paper made through the app for the `papers9` gate (Increment 9): copy its evidence into the repo.

    uv run python scripts/record_papers9.py <run_id> --kind remade --notes "what changed, what still reads wrong" [--by NAME --attribution TEXT]

As `record_paper_demo.py` (Increment 6), into `data/papers9/<run_id>/`, with the paper's sentence records, the
targeted search's report and any works it added. The passages are not copied. Spend, caps, lights and the kept and
removed counts are never typed here: `tools/checks/check_papers9.py` reads them from the copied files.
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
    ap.add_argument("--kind", choices=["remade"], required=True, help="remade: an Increment 7 paper made again")
    ap.add_argument("--notes", required=True, help="notes on the paper by whoever made it")
    ap.add_argument("--by", default="", help="who made the paper (default: the git user)")
    ap.add_argument("--attribution", default="", help="required when it is not Chris: who, at whose request")
    args = ap.parse_args()
    run_dir, out = ROOT / "runs" / args.run_id, ROOT / "data" / "papers9" / args.run_id
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
    who = args.by or subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=False).stdout.strip()
    if who not in ("Chris", "Chris Schmidt") and not args.attribution.strip():
        raise SystemExit("--attribution is required when the paper was not made by Chris")
    record_path = ROOT / "data" / "papers9" / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {"papers": []}
    record["papers"] = [p for p in record["papers"] if p["run_id"] != args.run_id]
    record["papers"].append({"run_id": args.run_id, "kind": args.kind, "notes": args.notes, "made_by": who or "unknown", "attribution": args.attribution.strip() or None,
                             "recorded_at": datetime.now(UTC).isoformat(timespec="seconds")})  # fmt: skip
    record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"recorded {args.run_id} ({args.kind}) in data/papers9/ ({len(record['papers'])} papers on record)")


if __name__ == "__main__":
    main()
