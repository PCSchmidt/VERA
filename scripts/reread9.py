# ruff: noqa: E501
"""Re-read Increment 8's five re-audits under the Increment 9 rule (AUD-F-14), without a model call.

Every finding in `data/reaudit8/<paper>/audit_report.json` stores its verdicts: the audit's judge and, where it was asked,
the reference judge (`sonnet-ref`). A failure the reference was asked about is re-settled by
`vera.audit.disagreement.outcome`, the function the audit itself now uses: a confident reference no keeps it a failure, a
confident yes makes it a disagreement (already a warning since Increment 8), and an answer below 0.7 either way makes it
unsettled (a warning). No verdict changes; only severities. Writes `data/results/reread9.json` with, per paper, the light
and the failures, disagreements and unsettled findings before and after.

    uv run python scripts/reread9.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.audit import disagreement  # noqa: E402

PAPERS = ("P1", "P2", "P3", "N1", "N2")
REFERENCE = "sonnet-ref"


def light(findings: list[dict]) -> str:
    severities = {f["severity"] for f in findings}
    return "red" if "fail" in severities else "amber" if "warn" in severities else "green"


def tally(findings: list[dict]) -> dict:
    return {"light": light(findings), "fails": sum(f["severity"] == "fail" for f in findings),
            "disagreements": sum(f["summary"].startswith(disagreement.PREFIX) for f in findings),
            "unsettled": sum(f["summary"].startswith(disagreement.UNSETTLED) for f in findings)}  # fmt: skip


def reread(findings: list[dict]) -> tuple[list[dict], Counter]:
    out, moved = [], Counter()
    for f in findings:
        verdicts = f.get("verdicts") or []
        refs = [v for v in verdicts if v["backend"] == REFERENCE]
        cheap = [v for v in verdicts if v["backend"] != REFERENCE]
        if f["severity"] != "fail" or f["check"] not in ("sentence", "inference") or not refs or not cheap:
            out.append(f)
            continue
        kind, why = disagreement.outcome(SimpleNamespace(**cheap[-1]), SimpleNamespace(**refs[-1]), None)
        moved[kind] += 1
        if kind == "fail":
            out.append(f)
        else:
            prefix = disagreement.PREFIX if kind == "disagree" else disagreement.UNSETTLED
            out.append({**f, "severity": "warn", "summary": f"{prefix} ({why}): {f['summary']}"})
    return out, moved


def main() -> None:
    result = {"source": "data/reaudit8/*/audit_report.json", "papers": {}}
    for label in PAPERS:
        report = json.loads((ROOT / "data" / "reaudit8" / label / "audit_report.json").read_text(encoding="utf-8"))
        after, moved = reread(report["findings"])
        assert [f.get("verdicts") for f in after] == [f.get("verdicts") for f in report["findings"]]  # no verdict changes
        result["papers"][label] = {"before": tally(report["findings"]), "after": tally(after), "failures_resettled": dict(moved)}
        print(label, result["papers"][label])
    (ROOT / "data" / "results" / "reread9.json").write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
