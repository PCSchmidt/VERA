# ruff: noqa: E501
"""Papers made again, and a fresh one (gate `paper_rerun`, Increment 7, SPEC "Papers made again, and a fresh one").

Blocks unless:
- the three Increment 6 papers were re-audited with the Increment 7 audit (`scripts/reaudit_incr6.py`): each report in
  `data/paper_rerun/reaudit/<run>/` ran the sentence check, and the re-audit's spend is within its $0.50 cap;
- `data/paper_rerun/record.json` lists a remade P2 (`discuss-the-evolution-of-prompting-guv8`) and a new paper from a
  review not used in Increment 6, each with its maker's own notes; each copied run (`scripts/record_paper_rerun.py`) has a
  finished paper made with sentence statuses, an audit that ran the sentence check, and the paper's spend, read from the
  run's ledger as what it spent after the review, within its cap.
Nothing here is taken from typed figures. Exit 0 passes, exit 2 blocks.
"""

from __future__ import annotations

import json
from collections import Counter

from _common import block, ok, repo_root_arg

INCR6 = ["how-much-useable-information-about-6x3n", "discuss-the-evolution-of-prompting-guv8", "rlm-vs-clm-3"]
REMADE = "discuss-the-evolution-of-prompting-guv8"
REAUDIT_CAP_USD = 0.50
MIN_NOTE_CHARS = 20


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    base = root / "data" / "paper_rerun"
    lines = []
    for run_id in INCR6:
        report_path = base / "reaudit" / run_id / "audit_report.json"
        if not report_path.exists():
            block(f"{run_id} not re-audited (scripts/reaudit_incr6.py)")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if "sentence" not in report["checks_run"]:
            block(f"{run_id}: the re-audit did not run the sentence check")
        before = json.loads((root / "data" / "paper_demo" / run_id / "paper" / "audit_report.json").read_text(encoding="utf-8"))["overall"]
        fails = Counter(f["check"] for f in report["findings"] if f["severity"] == "fail")
        lines.append(f"{run_id} re-audited {before}->{report['overall']} (fails {dict(fails)})")
    ledger = root / "data" / "ledger" / "reaudit_incr7.jsonl"
    spent = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()) if ledger.exists() else 0.0
    if spent > REAUDIT_CAP_USD:
        block(f"the re-audits spent ${spent:.4f}, over their ${REAUDIT_CAP_USD:.2f} cap")
    record = base / "record.json"
    if not record.exists():
        block("data/paper_rerun/record.json not found (scripts/record_paper_rerun.py after each paper)")
    papers = json.loads(record.read_text(encoding="utf-8"))["papers"]
    kinds = {p["kind"]: p for p in papers}
    if "remade" not in kinds or kinds["remade"]["run_id"] != REMADE:
        block(f"no remade paper from P2's review ({REMADE}) on record")
    if "new" not in kinds or kinds["new"]["run_id"] in INCR6:
        block("no new paper from a review not used in Increment 6 on record")
    for p in (kinds["remade"], kinds["new"]):
        folder = base / p["run_id"]
        notes = str(p.get("notes") or "").strip()
        if len(notes) < MIN_NOTE_CHARS or not any(ch.isalpha() for ch in notes):
            block(f"{p['run_id']}: no notes from the person who made it")
        for rel in ("paper/paper.json", "paper/audit_report.json", "paper/app_paper_request.json", "paper/app_state.json", "ledger.jsonl"):
            if not (folder / rel).exists():
                block(f"{p['run_id']}: {rel} not copied (scripts/record_paper_rerun.py)")
        state = json.loads((folder / "paper" / "app_state.json").read_text(encoding="utf-8")).get("state")
        if state != "complete":
            block(f"{p['run_id']}: the paper's state is {state!r}, not complete")
        doc = json.loads((folder / "paper" / "paper.json").read_text(encoding="utf-8"))
        if not doc.get("sentences"):
            block(f"{p['run_id']}: the paper has no sentence records (made before the Increment 7 checks?)")
        report = json.loads((folder / "paper" / "audit_report.json").read_text(encoding="utf-8"))
        if "sentence" not in report["checks_run"]:
            block(f"{p['run_id']}: its audit did not run the sentence check")
        req = json.loads((folder / "paper" / "app_paper_request.json").read_text(encoding="utf-8"))
        rows = (folder / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        paper_spent = sum(json.loads(ln)["cost_usd"] for ln in rows if ln.strip()) - req["spent_before_usd"]
        cap = req["request"]["max_usd"]
        if paper_spent > cap + 1e-9:
            block(f"{p['run_id']}: the paper spent ${paper_spent:.4f}, over its ${cap:.2f} cap")
        sents = doc["sentences"]
        removed = Counter(s["kind"] for s in sents if s["status"] != "pass")
        lines.append(f"{p['run_id']} ({p['kind']}): ${paper_spent:.3f} of ${cap:.2f}, {report['overall']}, {len(doc['claims'])} claims, "
                     f"{len(sents)} sentences, removed {dict(removed)}")
    ok("; ".join(lines) + f"; re-audit spend ${spent:.4f}")


if __name__ == "__main__":
    main()
