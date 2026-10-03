"""Account for every `lit.*` and `loop.*` verdict this increment's runs recorded: used, or excluded and why.

Reads runs/<id>/gates.jsonl of the three topic runs and the loop runs given, counts the records by question id, and
writes data/retest3/accounting.json with, per question id, how many records there are and what became of them. A record
is "used" when a re-test measured the judge on that decision; otherwise it is excluded with the reason (no label, or
measured by a different check). Nothing is dropped without a line here.

Usage: uv run python scripts/verdict_accounting.py topic-a-loop-1 topic-a-loop-2
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REASONS = {
    "lit.relevant": "measured by the retrieval check: the screen against 45 helper-labelled candidates "
    "(docs/results/retrieval_recall.md, data/retrieval/relevance_check.csv)",
    "lit.claim_supported": "used: the constructed claim benchmark and the 30 real claims labelled by an AI helper "
    "(data/claim_bench/); the other records are the same claims asked again (repairs, the final audit)",
    "lit.question_scoped": "excluded: no label (one verdict per topic, the user confirms the question)",
    "lit.section_answers": "excluded: no label (one verdict per section, read by the user and the rubric scorers)",
    "lit.evidence_sufficient": "excluded: no label (one verdict per topic)",
    "lit.parent_fits": "excluded: no label (the user's reading of the selection is the check)",
    "lit.parent_refusal": "excluded: no label (the user's reading of the refusal is the check)",
    "loop.baseline_reproduced": "used: re-test of the loop's gates (data/retest3), label = the programmatic shadow",
    "loop.beats_baseline": "used: re-test of the loop's gates (data/retest3), label = the shadow answer",
    "loop.best_method": "used: re-test of the loop's gates (data/retest3), label = the shadow answer",
    "loop.guidance_met": "excluded: no shadow answer (free-text constraints in the guidance)",
    "loop.idea_worth_run": "reported separately: a Score with no computable label (distribution and outcome in "
    "data/retest3/results.json)",
}


def main() -> None:
    topics = json.loads((ROOT / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    topic_runs = [
        json.loads((ROOT / "data" / "topics" / f"scope_{t}.json").read_text(encoding="utf-8"))["run_id"] for t in topics
    ]
    all_runs = [*topic_runs, *sys.argv[1:]]
    counts: Counter[str] = Counter()
    for run in all_runs:
        path = ROOT / "runs" / run / "gates.jsonl"
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                q = json.loads(ln)["question"]["id"]
                if q.startswith(("lit.", "loop.")):
                    counts[q] += 1
    unaccounted = sorted(set(counts) - set(REASONS))
    if unaccounted:
        raise SystemExit(f"question ids with no stated disposition: {unaccounted}")
    out = {"runs": all_runs, "records": sum(counts.values()),
           "by_question": {q: {"records": n, "disposition": REASONS[q]}
                           for q, n in sorted(counts.items())}}  # fmt: skip
    (ROOT / "data" / "retest3").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "retest3" / "accounting.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for q, v in out["by_question"].items():
        print(f"{q:28} {v['records']:5}  {v['disposition'][:80]}")


if __name__ == "__main__":
    main()
