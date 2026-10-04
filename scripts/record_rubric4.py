# ruff: noqa: E501
"""Record a person's (or the independent scorer's) rubric scores for one Increment 4 output (SPEC "Rubric scoring (human, blind)").

Each output is scored 1 to 5 on five criteria: answers the question, coverage, correctness, reproducibility, honesty about limits
(docs/results/rubric_sheet_4.md says what each means and which files to read). Scores go to data/results/rubric4_<who>.json, one
entry per output with the name, the time and whether the scorer says it was blind; recording an output again appends a new entry
and never replaces the old one.

`--blind` is the scorer's statement that they have not read the independent scorer's scores (data/results/rubric4_evaluator.json) for
this set. The script refuses `--blind` from anyone but the independent scorer if that file already exists, because the scores were then
there to read. The independent scorer runs afterwards, on the same files.

Outputs: L1 research-agents-eval review, L2 conformal-shift review, L3 tabular-trees-vs-nets review, L4 tree-explain review,
L5 credal-dro review, L6 llm-judge-numbers review, P1 tree-explain paper, P2 credal paper.

Usage: uv run python scripts/record_rubric4.py L1 --by Chris --blind 3 2 4 4 4 --note "why, in a line"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("L1", "L2", "L3", "L4", "L5", "L6", "P1", "P2")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty")
INDEPENDENT = "evaluator"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", choices=OUTPUTS)
    ap.add_argument("scores", type=int, nargs=len(CRITERIA), help="1-5 for each criterion, in the documented order")
    ap.add_argument("--by", required=True, help="who is scoring")
    ap.add_argument("--blind", action="store_true", help="I have not read the independent scorer's scores")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    if not all(1 <= s <= 5 for s in args.scores):
        raise SystemExit("each score is 1 to 5")
    results = ROOT / "data" / "results"
    if args.blind and args.by.lower() != INDEPENDENT and (results / f"rubric4_{INDEPENDENT}.json").exists():
        raise SystemExit("the independent scorer's file already exists: scores given now cannot be marked blind")
    path = results / f"rubric4_{args.by.lower()}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"by": args.by, "entries": []}
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["entries"].append({"output": args.output, "at": stamp, "blind": bool(args.blind), "note": args.note,
                            "scores": dict(zip(CRITERIA, args.scores, strict=True))})  # fmt: skip
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    done = sorted({e["output"] for e in data["entries"]})
    print(f"{args.by}: {args.output} recorded {args.scores} (blind: {args.blind}); scored so far: {', '.join(done)}; "
          f"still to score: {', '.join(o for o in OUTPUTS if o not in done) or 'none'}")


if __name__ == "__main__":
    main()
