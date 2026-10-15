# ruff: noqa: E501
"""Two papers made again with the Increment 9 write step and rule (gate `papers9`, SPEC "Two papers made again").

Blocks unless `data/papers9/record.json` lists N1 (`discuss-the-evolution-of-prompting-guv8`) and N2 (`rlm-vs-clm-2`), each
with notes and the name of who made it (and an attribution when it was not Chris), and each copied run
(`scripts/record_papers9.py`) shows a finished paper with sentence records, an audit that ran the sentence check, and the
paper's spend, read from the run's ledger as what it spent after the review, within its cap. Reports the write-time
confirmations from the stored verdicts (reference verdicts on sentences and statements, and what they decided) and the
audit's failures, disagreements and unsettled findings. Nothing here is taken from typed figures. Exit 0 passes, exit 2 blocks.
"""

from __future__ import annotations

import json
from collections import Counter

from _common import block, ok, repo_root_arg

RUNS = {"N1": "discuss-the-evolution-of-prompting-guv8", "N2": "rlm-vs-clm-2"}
REFERENCE = "sonnet-ref"
MIN_NOTE_CHARS = 20


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    base = root / "data" / "papers9"
    record = base / "record.json"
    if not record.exists():
        block("data/papers9/record.json not found (scripts/record_papers9.py after each paper)")
    papers = {p["run_id"]: p for p in json.loads(record.read_text(encoding="utf-8"))["papers"]}
    lines = []
    for label, run_id in RUNS.items():
        p = papers.get(run_id)
        if p is None:
            block(f"{label} ({run_id}) not on record")
        if len(str(p.get("notes") or "").strip()) < MIN_NOTE_CHARS:
            block(f"{label}: no notes")
        if p.get("made_by") not in ("Chris", "Chris Schmidt") and not str(p.get("attribution") or "").strip():
            block(f"{label}: made by {p.get('made_by')!r} without an attribution")
        folder = base / run_id
        for rel in ("paper/paper.json", "paper/audit_report.json", "paper/app_paper_request.json", "paper/app_state.json", "ledger.jsonl"):
            if not (folder / rel).exists():
                block(f"{label}: {rel} not copied")
        if json.loads((folder / "paper" / "app_state.json").read_text(encoding="utf-8")).get("state") != "complete":
            block(f"{label}: the paper is not complete")
        doc = json.loads((folder / "paper" / "paper.json").read_text(encoding="utf-8"))
        if not doc.get("sentences"):
            block(f"{label}: no sentence records")
        report = json.loads((folder / "paper" / "audit_report.json").read_text(encoding="utf-8"))
        if "sentence" not in report["checks_run"]:
            block(f"{label}: its audit did not run the sentence check")
        req = json.loads((folder / "paper" / "app_paper_request.json").read_text(encoding="utf-8"))
        rows = (folder / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        spent = sum(json.loads(ln)["cost_usd"] for ln in rows if ln.strip()) - req["spent_before_usd"]
        if spent > req["request"]["max_usd"] + 1e-9:
            block(f"{label}: spent ${spent:.4f}, over its ${req['request']['max_usd']:.2f} cap")
        items = [*doc["sentences"], *doc["inferences"]]
        refs = Counter(("yes" if v["answer"] is True else "no") + ("" if v["confidence"] >= 0.7 else " (unsure)")
                       for it in items for v in it.get("verdicts") or [] if v["backend"] == REFERENCE)  # fmt: skip
        f = report["findings"]
        tally = {"fails": sum(x["severity"] == "fail" for x in f), "disagree": sum(x["summary"].startswith("judges disagree") for x in f),
                 "unsettled": sum(x["summary"].startswith("unsettled") for x in f)}  # fmt: skip
        lines.append(f"{label}: ${spent:.3f}, {report['overall']}, {tally}, write-time reference {dict(refs)}")
    ok("; ".join(lines))


if __name__ == "__main__":
    main()
