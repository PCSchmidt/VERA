# ruff: noqa: E501
"""Re-audit the three Increment 6 papers with the Increment 7 audit (SPEC "Papers made again, and a fresh one", part a).

No rewriting: each paper is audited as it was made, on a temporary copy of its live run (`runs/<run>/`, which holds the
passages the audit needs), so the run's own Increment 6 audit is not overwritten. The new audit adds the sentence audit
(AUD-F-12) and the clause-by-clause interpretation check; a paper made before sentence statuses is split into sentences.
Writes `data/paper_rerun/reaudit/<run>/audit_report.json` and `audit.md` (the passages are not copied into the repo) and
prints the light before (Increment 6, `data/paper_demo`) and after. Judge calls go through the cheap path with the key in
`.env`, into `data/ledger/reaudit_incr7.jsonl`, capped at $0.50 for all three (SPEC).

    uv run python scripts/reaudit_incr6.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.app import pipeline  # noqa: E402
from vera.judge.cheap_path import cheap_path  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.literature.deps import LitDeps  # noqa: E402
from vera.schemas import Budget, RunRequest  # noqa: E402

RUNS = ["how-much-useable-information-about-6x3n", "discuss-the-evolution-of-prompting-guv8", "rlm-vs-clm-3"]
CAP_USD = 0.50
OUT = ROOT / "data" / "paper_rerun" / "reaudit"


def main() -> None:
    ledger_path = ROOT / "data" / "ledger" / "reaudit_incr7.jsonl"
    earlier = sum(r.cost_usd for r in Ledger(ledger_path).records()) if ledger_path.exists() else 0.0
    if earlier >= CAP_USD:
        sys.exit(f"the re-audit cap (${CAP_USD:.2f}) is spent")
    ledger = Ledger(ledger_path, run_id="reaudit_incr7")
    budget = Budget(max_usd=CAP_USD - earlier, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="p2.reaudit_incr7")
    for run_id in RUNS:
        live = ROOT / "runs" / run_id
        if not (live / "paper" / "passages.jsonl").exists():
            sys.exit(f"{live}/paper/passages.jsonl not found: the re-audit needs the live run")
        before = json.loads((ROOT / "data" / "paper_demo" / run_id / "paper" / "audit_report.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / run_id
            shutil.copytree(live, run_dir, ignore=shutil.ignore_patterns("checkpoints.sqlite*", "worker.log"))
            request = RunRequest.model_validate(json.loads((live / "app_request.json").read_text(encoding="utf-8")))
            deps = LitDeps(spec=pipeline.make_spec(request), generator=None, judge=judge, budget=budget, run_dir=run_dir, ledger=ledger)
            light = pipeline.run_paper_audit(deps, judge=judge)
            dest = OUT / run_id
            dest.mkdir(parents=True, exist_ok=True)
            for name in ("audit_report.json", "audit.md"):
                shutil.copy(run_dir / "paper" / name, dest / name)
        report = json.loads((dest / "audit_report.json").read_text(encoding="utf-8"))
        kinds = Counter((f["check"], f["severity"]) for f in report["findings"])
        print(f"{run_id}: {before['overall']} -> {light}; findings {dict(kinds)}")
    print(f"spend ${sum(r.cost_usd for r in Ledger(ledger_path).records()):.4f} of ${CAP_USD:.2f}")


if __name__ == "__main__":
    main()
