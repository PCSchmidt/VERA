# ruff: noqa: E501
"""Re-read the two Increment 9 papers' audits with the reference's write-time answer kept (Increment 10), no model call.

Each failure, disagreement or unsettled finding in `data/papers9/<run>/paper/audit_report.json` whose item (sentence or
statement, by id) has a stored write-time reference verdict on the same question is re-settled with that stored verdict
in place of the audit's second reference answer, by `vera.audit.disagreement.outcome`, the function the audit uses. The
item text is unchanged (the audit read the paper as written). Writes `data/results/sticky10.json` with each paper's
findings before and after, and which items moved.

    uv run python scripts/reread10.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.audit import disagreement  # noqa: E402

RUNS = {"N1": "discuss-the-evolution-of-prompting-guv8", "N2": "rlm-vs-clm-2"}
REFERENCE = "sonnet-ref"


def tally(findings: list[dict]) -> dict:
    sev = {f["severity"] for f in findings}
    return {"light": "red" if "fail" in sev else "amber" if "warn" in sev else "green",
            "fails": sum(f["severity"] == "fail" for f in findings),
            "disagreements": sum(f["summary"].startswith(disagreement.PREFIX) for f in findings),
            "unsettled": sum(f["summary"].startswith(disagreement.UNSETTLED) for f in findings)}  # fmt: skip


def main() -> None:
    out = {"source": "data/papers9/*/paper/", "papers": {}}
    for label, run in RUNS.items():
        folder = ROOT / "data" / "papers9" / run / "paper"
        doc = json.loads((folder / "paper.json").read_text(encoding="utf-8"))
        report = json.loads((folder / "audit_report.json").read_text(encoding="utf-8"))
        records = {r["id"]: r for r in [*doc["sentences"], *doc["inferences"]]}
        after, moved = [], []
        for f in report["findings"]:
            verdicts = f.get("verdicts") or []
            cheap = [v for v in verdicts if v["backend"] != REFERENCE]
            item = records.get(f["evidence"][0]["claim_id"]) if f.get("evidence") else None
            if f["check"] not in ("sentence", "inference") or not cheap or item is None:
                after.append(f)
                continue
            qid = cheap[-1]["question_id"]
            stored = [v for v in item.get("verdicts") or [] if v["backend"] == REFERENCE and v["question_id"] == qid]
            if not stored:
                after.append(f)
                continue
            kind, why = disagreement.outcome(SimpleNamespace(**cheap[-1]), SimpleNamespace(**stored[-1]), None)
            base = f["summary"].split("): ", 1)[1] if f["summary"].startswith((disagreement.PREFIX, disagreement.UNSETTLED)) else f["summary"]
            new = {**f, "severity": "fail", "summary": base} if kind == "fail" else {
                **f, "severity": "warn", "summary": f"{disagreement.PREFIX if kind == 'disagree' else disagreement.UNSETTLED} ({why}): {base}"}
            if (new["severity"], new["summary"][:12]) != (f["severity"], f["summary"][:12]):
                moved.append({"item": item["id"], "from": f["severity"] + " " + f["summary"][:10], "to": kind,
                              "stored_reference": [stored[-1]["answer"], stored[-1]["confidence"]]})  # fmt: skip
            after.append(new)
        out["papers"][label] = {"before": tally(report["findings"]), "after": tally(after), "moved": moved}
        print(label, out["papers"][label])
    (ROOT / "data" / "results" / "sticky10.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
