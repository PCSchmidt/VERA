"""Run a topic through the literature stage: scope, then (after confirmation) the stages that follow (Increment 3).

Phase 1 (`--phase start`) scopes the topic under the scoping cap and stops: it prints the proposed question. Confirm it
with scripts/confirm_scope.py, then phase 2 (`--phase continue`) resumes from the checkpoint with the run's full budget.
One run = one directory runs/<run_id>/ and one never-overwritten ledger data/ledger/run_<run_id>.jsonl.

Needs OPENROUTER_API_KEY and TYPESAFE_AI_API_KEY in .env, and data/topics/<topic>.json (the approved topic).

Usage:
  uv run python scripts/run_topic.py --topic tree-explain --run-id topic-a-1 --max-usd 2 --phase start
  uv run python scripts/confirm_scope.py topic-a-1 --by Chris --accept
  uv run python scripts/run_topic.py --topic tree-explain --run-id topic-a-1 --max-usd 2 --phase continue
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera.backends.generator import OpenRouterGenerator
from vera.judge.cheap_path import cheap_path
from vera.keepawake import keep_awake
from vera.ledger import Ledger
from vera.literature.deps import LitDeps
from vera.literature.graph import continue_topic_run, start_topic_run
from vera.schemas import Budget, OutputGuidance, RunSpec, Topic

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ("sonnet", "anthropic/claude-sonnet-5.5")  # T9: Sonnet 5.5 for every stage
REASONING = {"effort": "minimal"}
GUIDANCE = OutputGuidance(
    format="paper", max_words=1500,
    emphasis="Say plainly what the literature establishes and what it does not; cite only retrieved sources.",
    constraints=["forbid: state of the art", "forbid: breakthrough"],
)  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, help="id of data/topics/<id>.json")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--phase", choices=["start", "continue"], required=True)
    ap.add_argument("--max-usd", type=float, default=2.0)
    ap.add_argument("--scope-cap", type=float, default=0.25)
    ap.add_argument("--max-wall", type=int, default=7200)
    ap.add_argument("--max-tokens", type=int, default=8000)
    args = ap.parse_args()

    topic_file = ROOT / "data" / "topics" / f"{args.topic}.json"
    info = json.loads(topic_file.read_text(encoding="utf-8"))
    hint = f"{info['path_note']} A good question: {info['good_question']}"  # never the key papers (no peeking)
    topic = Topic(id=info["id"], text=info["text"], scope_hint=hint,
                  key_papers_ref=topic_file.relative_to(ROOT).as_posix())  # fmt: skip
    spec = RunSpec(run_id=args.run_id, topic=topic, guidance=GUIDANCE,
                   budget=Budget(max_usd=args.max_usd, max_wall_seconds=args.max_wall),
                   models={"scope": GENERATOR[0]})  # fmt: skip
    ledger = Ledger.for_run(args.run_id, root=ROOT / "data" / "ledger", resume=args.phase == "continue")
    budget = spec.budget.model_copy()
    generator = OpenRouterGenerator(
        GENERATOR[0], GENERATOR[1], ledger=ledger, budget=budget, max_tokens=args.max_tokens, reasoning=REASONING
    )
    deps = LitDeps(
        spec=spec, generator=generator, judge=cheap_path(ledger=ledger, budget=budget), budget=budget,
        run_dir=ROOT / "runs" / args.run_id, ledger=ledger, scope_cap_usd=args.scope_cap,
    )  # fmt: skip
    with keep_awake():
        state = start_topic_run(deps) if args.phase == "start" else continue_topic_run(deps)
    stop = state.get("stop")
    print(f"trail: {' > '.join(state['trail'])}")
    print(f"status: {stop['stage'] + ': ' + stop['reason'] if stop else 'complete'}")
    print(f"spent: ${deps.budget.spent_usd:.4f}; ledger {ledger.path.relative_to(ROOT)}")
    if args.phase == "start":
        print(f"\nnext: uv run python scripts/confirm_scope.py {args.run_id} --show")


if __name__ == "__main__":
    main()
