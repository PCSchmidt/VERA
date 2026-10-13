# ruff: noqa: E501
"""Papers made through the app from real reviews (gate `paper_demo`, Increment 6, SPEC "Papers from real reviews").

Blocks unless `data/paper_demo/record.json` lists at least three runs, each with its owner's own notes, and each run's
copied files (`scripts/record_paper_demo.py`) show: a finished paper with an audit report; the paper's spend, read from
the run's own ledger as what it spent after the review, within the paper's cap; the paper's request as the app wrote it.
Nothing here is taken from typed figures. Exit 0 passes, exit 2 blocks.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

MIN_PAPERS = 3
MIN_NOTE_CHARS = 20


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    base = root / "data" / "paper_demo"
    record = base / "record.json"
    if not record.exists():
        block("data/paper_demo/record.json not found (scripts/record_paper_demo.py after each paper)")
    papers = json.loads(record.read_text(encoding="utf-8"))["papers"]
    if len(papers) < MIN_PAPERS:
        block(f"{len(papers)} papers on record; the SPEC asks for {MIN_PAPERS}")
    lines = []
    for p in papers:
        folder = base / p["run_id"]
        notes = str(p.get("notes") or "").strip()
        if len(notes) < MIN_NOTE_CHARS or not any(ch.isalpha() for ch in notes):
            block(f"{p['run_id']}: no notes from the person who made it (a placeholder such as '...' is not a note)")
        for rel in ("paper/paper.json", "paper/audit_report.json", "paper/app_paper_request.json", "ledger.jsonl"):
            if not (folder / rel).exists():
                block(f"{p['run_id']}: {rel} not copied (scripts/record_paper_demo.py)")
        req = json.loads((folder / "paper" / "app_paper_request.json").read_text(encoding="utf-8"))
        ledger = (folder / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        spent = sum(json.loads(ln)["cost_usd"] for ln in ledger if ln.strip()) - req["spent_before_usd"]
        cap = req["request"]["max_usd"]
        if spent > cap + 1e-9:
            block(f"{p['run_id']}: the paper spent ${spent:.4f}, over its ${cap:.2f} cap")
        state = json.loads((folder / "paper" / "app_state.json").read_text(encoding="utf-8")).get("state")
        if state != "complete":
            block(f"{p['run_id']}: the paper's state is {state!r}, not complete")
        doc = json.loads((folder / "paper" / "paper.json").read_text(encoding="utf-8"))
        light = json.loads((folder / "paper" / "audit_report.json").read_text(encoding="utf-8"))["overall"]
        kept = sum(1 for i in doc["inferences"] if i["status"] == "pass")
        lines.append(f"{p['run_id']}: ${spent:.3f} of ${cap:.2f}, {light}, {len(doc['claims'])} claims, {kept}/{len(doc['inferences'])} statements kept")
    ok("; ".join(lines))


if __name__ == "__main__":
    main()
