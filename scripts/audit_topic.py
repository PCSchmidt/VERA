"""The final audit of a topic run's literature section (AUD-F-03 and AUD-F-10 on the loop's own text).

Runs `vera.audit.run_literature_audit` on runs/<run_id>/literature.md with its claims, the passages it may quote and
its retrieval log, through the cheap judge path (the section's producer is `p3.synthesize`, so no judge grades its own
text). Writes runs/<run_id>/artifacts/audit_report.json and runs/<run_id>/audit.md, and appends the judge calls to the
run's ledger. The report is green, amber or red; red is reported, not hidden, and does not rewrite the section.

Usage: uv run python scripts/audit_topic.py scope-tree-explain-2 scope-credal-dro-2 scope-llm-judge-numbers-3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera import audit
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
MIN_CONFIDENCE = 0.7


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def audit_run(run_id: str, max_usd: float) -> dict:
    run_dir = ROOT / "runs" / run_id
    ledger = Ledger.for_run(run_id, root=ROOT / "data" / "ledger", resume=True)
    budget = Budget(max_usd=max_usd, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget)

    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        verdict = verdict.model_copy(update={"producer_id": "p3.synthesize"})
        return verdict, verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE

    run = audit.run_literature_audit(
        (run_dir / "literature.md").read_text(encoding="utf-8"), jsonl(run_dir / "claims.jsonl"),
        jsonl(run_dir / "passages.jsonl"), jsonl(run_dir / "retrieved.jsonl"), ask=ask, paper_id=run_id,
        paper_source="literature.md",
    )  # fmt: skip
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    report = run.report
    (run_dir / "artifacts" / "audit_report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "audit.md").write_text(audit.render_markdown(run), encoding="utf-8")
    return {"run_id": run_id, "overall": report.overall, "claims": len(run.claims),
            "fail": sum(f.severity == "fail" for f in report.findings),
            "warn": sum(f.severity == "warn" for f in report.findings),
            "cost_usd": round(budget.spent_usd, 5)}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_ids", nargs="+")
    ap.add_argument("--max-usd", type=float, default=0.25)
    args = ap.parse_args()
    for run_id in args.run_ids:
        print(json.dumps(audit_run(run_id, args.max_usd)))


if __name__ == "__main__":
    main()
