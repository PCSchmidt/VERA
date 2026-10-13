# ruff: noqa: E501
"""Record rubric scores for one Increment 6 review paper (SPEC "Rubric scoring of the papers"; docs/results/rubric_sheet_6.md).

Each paper is scored 1 to 5 on six criteria (answers the question, coverage, correctness, reproducibility, honesty about limits,
interpretation follows from evidence) and given a preference against the review it came from (paper, review or same). Scores go to
data/results/rubric6_<who>.json; recording a paper again appends a new entry and never replaces the old one.

`--blind` is the scorer's statement that they have not read the independent scorer's scores; it is refused from anyone but the
independent scorer once that file exists. `--helped-by` names any model that helped form the score (it is reported, not hidden).

Usage: uv run python scripts/record_rubric6.py P1 --by Chris --blind 3 3 3 4 4 3 --prefer paper --note "why, in a line"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("P1", "P2", "P3")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty", "interpretation_follows")
INDEPENDENT = "evaluator"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", choices=OUTPUTS)
    ap.add_argument("scores", type=int, nargs=len(CRITERIA), help="1-5 for each criterion, in the documented order")
    ap.add_argument("--by", required=True, help="who is scoring")
    ap.add_argument("--blind", action="store_true", help="I have not read the independent scorer's scores")
    ap.add_argument("--prefer", required=True, choices=("paper", "review", "same"))
    ap.add_argument("--helped-by", default="", help="any model that helped form this score")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    if not all(1 <= s <= 5 for s in args.scores):
        raise SystemExit("each score is 1 to 5")
    results = ROOT / "data" / "results"
    if args.blind and args.by.lower() != INDEPENDENT and (results / f"rubric6_{INDEPENDENT}.json").exists():
        raise SystemExit("the independent scorer's file already exists: scores given now cannot be marked blind")
    path = results / f"rubric6_{args.by.lower()}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"by": args.by, "entries": []}
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["entries"].append({"output": args.output, "at": stamp, "blind": bool(args.blind), "prefer": args.prefer,
                            "helped_by": args.helped_by.strip() or None, "note": args.note,
                            "scores": dict(zip(CRITERIA, args.scores, strict=True))})  # fmt: skip
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    done = sorted({e["output"] for e in data["entries"]})
    print(f"{args.by}: {args.output} recorded {args.scores}, prefers {args.prefer} (blind: {args.blind}); "
          f"still to score: {', '.join(o for o in OUTPUTS if o not in done) or 'none'}")  # fmt: skip


if __name__ == "__main__":
    main()
