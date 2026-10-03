"""Write a topic's literature section again from the evidence an earlier run already gathered, in a new run directory.

For measuring a change to the synthesis stage (Increment 4: the anchoring rule) without touching the earlier run: it
copies `retrieved.jsonl`, `passages.jsonl` and `scope.json` from runs/<source> into runs/<new>/, rebuilds the little
state the synthesis nodes need from the source's artifacts, and runs `synthesize` then `verify` with the current code,
Sonnet 5.5 as the generator and the cheap judge path, in the new run's own ledger. The source run is never modified.
The new section is a dev measurement (the old topics' key lists are no longer independent), not a replacement of the
committed sections.



Usage: uv run python scripts/resynthesize.py scope-tree-explain-2 resynth-tree-1 --max-usd 0.5
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from vera.backends.generator import OpenRouterGenerator
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.literature import synthesis_stage
from vera.literature.deps import LitDeps
from vera.schemas import Budget, OutputGuidance, RunSpec, Topic

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("new")
    ap.add_argument("--max-usd", type=float, default=0.5)
    args = ap.parse_args()
    src, dst = ROOT / "runs" / args.source, ROOT / "runs" / args.new
    if dst.exists():
        raise SystemExit(f"runs/{args.new} exists: a new run id is needed")
    dst.mkdir(parents=True)
    for name in ("retrieved.jsonl", "passages.jsonl", "scope.json"):
        shutil.copy(src / name, dst / name)
    (dst / "artifacts").mkdir()
    scope = json.loads((dst / "scope.json").read_text(encoding="utf-8"))
    topic_id = scope["topic_id"]
    info = json.loads((ROOT / "data" / "topics" / f"{topic_id}.json").read_text(encoding="utf-8"))
    spec = RunSpec(run_id=args.new, topic=Topic(id=topic_id, text=info["text"]),
                   guidance=OutputGuidance(format="paper", max_words=1500),
                   budget=Budget(max_usd=args.max_usd, max_wall_seconds=3600),
                   models={"scope": "sonnet"})  # fmt: skip
    ledger = Ledger.for_run(args.new, root=ROOT / "data" / "ledger")
    budget = spec.budget.model_copy()
    generator = OpenRouterGenerator("sonnet", "anthropic/claude-sonnet-5.5", ledger=ledger, budget=budget,
                                    max_tokens=8000, reasoning={"effort": "minimal"})  # fmt: skip
    deps = LitDeps(spec=spec, generator=generator, judge=cheap_path(ledger=ledger, budget=budget), budget=budget,
                   run_dir=dst, ledger=ledger)  # fmt: skip
    records = [json.loads(ln) for ln in (dst / "retrieved.jsonl").read_text("utf-8").splitlines() if ln.strip()]
    report = json.loads((src / "artifacts" / "reading.json").read_text(encoding="utf-8"))["papers"]
    cited_or_read = {p["key"] for p in report}
    queries = json.loads((src / "artifacts" / "queries.json").read_text(encoding="utf-8"))["queries"]
    state = {"queries": queries, "records": [r["key"] for r in records], "kept": sorted(cited_or_read),
             "read_report": report, "trail": []}  # fmt: skip
    state |= synthesis_stage.synthesize_node(deps)(state)
    state |= synthesis_stage.verify_node(deps)(state)
    stats = json.loads((dst / "artifacts" / "literature.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "stop": state.get("stop"),
                "stats": stats["stats"],
                "failure_reasons": stats["failure_reasons"],
                "kept": stats["n_claims_kept"],
                "spent_usd": round(budget.spent_usd, 4),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
