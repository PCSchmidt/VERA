"""Re-audit finished runs' papers with the current audit code, so a comparison judges every arm by one audit version.

The audit changed while the generator comparison (docs/04 T9) was running (a method-section number and a bare percent
sign stopped counting as results claims), so the in-run audit reports of different waves came from different code. This
runs the *current* audit over each run's paper.md against its own results.json and retrieval log, writes
`runs/<run>/artifacts/audit_final.json`, and leaves the in-run report untouched. Judge calls go through the cheap path
into a never-overwritten ledger `data/ledger/run_reaudit-<n>.jsonl`.

Usage: uv run python scripts/reaudit_runs.py gen-*
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera.audit import render_markdown, run_audit
from vera.audit.bibliography import SourceLookup
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.loop import references
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "results" / "treehfd_baseline_target.json"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern", nargs="+", help="run directory names or globs under runs/")
    ap.add_argument("--max-usd", type=float, default=0.5)
    args = ap.parse_args()
    runs = sorted({p for pat in args.pattern for p in (ROOT / "runs").glob(pat) if (p / "paper.md").exists()})
    n = 1
    while (ROOT / "data" / "ledger" / f"run_reaudit-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"reaudit-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=args.max_usd, max_wall_seconds=3600)
    judge, lookup = cheap_path(ledger=ledger, budget=budget), SourceLookup()
    target = json.loads(TARGET.read_text(encoding="utf-8"))

    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        return verdict.model_copy(update={"producer_id": "p3.write_up"}), verdict.confidence >= 0.7

    for run in runs:
        results_file = run / "artifacts" / "results.json"
        if not results_file.exists():
            continue
        out = run_audit(
            (run / "paper.md").read_text(encoding="utf-8"), json.loads(results_file.read_text(encoding="utf-8")),
            references.load_references(run), ask=ask, lookup=lookup, paper_id=run.name, paper_source="paper.md",
            target=target,
        )  # fmt: skip
        (run / "artifacts" / "audit_final.json").write_text(
            json.dumps(out.report.model_dump(mode="json"), indent=1), encoding="utf-8"
        )
        (run / "audit_final.md").write_text(render_markdown(out), encoding="utf-8")
        counts = {s: sum(f.severity == s for f in out.report.findings) for s in ("fail", "warn", "info")}
        print(f"{run.name:22} {out.report.overall:5} {counts}")
    print(f"judge spend ${budget.spent_usd:.4f}; ledger {ledger.path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
