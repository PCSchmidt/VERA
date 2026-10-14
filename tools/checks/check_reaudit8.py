# ruff: noqa: E501
"""The five papers re-audited with the Increment 8 routing and rules (gate `reaudit8`, SPEC "The five papers re-audited").

Blocks unless `data/reaudit8/record.json` lists the five papers (P1-P3, N1, N2), each with a report in
`data/reaudit8/<paper>/` that ran the sentence check; the record names who ran it (with an attribution when it is not
Chris) and the route table it used, which matches the code's; and the re-audits' spend, read from their ledger, is within
the cap ($0.50, raised from the SPEC's $0.25 by Chris on 2026-10-14). Exit 0 passes, exit 2 blocks.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

PAPERS = ("P1", "P2", "P3", "N1", "N2")
CAP_USD = 0.50


def main() -> None:
    root = repo_root_arg(__doc__).parse_args().root
    base = root / "data" / "reaudit8"
    path = base / "record.json"
    if not path.exists():
        block("data/reaudit8/record.json not found (scripts/reaudit8.py)")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("run_by") != "Chris" and not str(record.get("attribution") or "").strip():
        block(f"run by {record.get('run_by')!r}, not Chris, and the record does not say at whose request")
    from vera.judge.cheap_path import QUESTION_ROUTES  # noqa: PLC0415

    if record.get("routes") != {k: list(v) for k, v in QUESTION_ROUTES.items()}:
        block("the record's routes differ from the code's route table")
    lines = []
    for label in PAPERS:
        entry = record["papers"].get(label)
        report_path = base / label / "audit_report.json"
        if entry is None or not report_path.exists():
            block(f"{label} not re-audited")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if "sentence" not in report["checks_run"]:
            block(f"{label}: the re-audit did not run the sentence check")
        b, a = entry["before"], entry["after"]
        lines.append(f"{label} {b['light']}->{a['light']} (fails {sum(b['fails'].values())}->{sum(a['fails'].values())}, disagreements {a['disagreements']})")
    ledger = root / "data" / "ledger" / "reaudit8.jsonl"
    spent = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()) if ledger.exists() else 0.0
    if spent > CAP_USD:
        block(f"the re-audits spent ${spent:.4f}, over their ${CAP_USD:.2f} cap")
    ok("; ".join(lines) + f"; spend ${spent:.4f} of ${CAP_USD:.2f}; run by {record['run_by']}")


if __name__ == "__main__":
    main()
