"""Record a person's rubric scores for one topic output (SPEC "Product bar and quality rubric").

Each output is scored 1 to 5 on five criteria: answers the question, coverage, correctness, reproducibility and honesty
about limits (docs/results/rubric_sheet.md says what each means and which files to read). Scores go to
data/results/rubric_<who>.json, one entry per output with the name and the time; recording an output again appends a new
entry and never replaces the old one. The independent reviewer's scores are in data/results/rubric_evaluator.json.

Usage: uv run python scripts/record_rubric.py A-lit --by Chris 3 2 4 4 4 --note "why, in a line"
       (the five numbers, in the order of the criteria above; outputs: A-lit, A-paper, B, C)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("A-lit", "A-paper", "B", "C")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", choices=OUTPUTS)
    ap.add_argument("scores", type=int, nargs=len(CRITERIA), help="1-5 for each criterion, in the documented order")
    ap.add_argument("--by", required=True, help="who is scoring")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    if not all(1 <= s <= 5 for s in args.scores):
        raise SystemExit("each score is 1 to 5")
    path = ROOT / "data" / "results" / f"rubric_{args.by.lower()}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"by": args.by, "entries": []}
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["entries"].append({"output": args.output, "at": stamp, "note": args.note,
                            "scores": dict(zip(CRITERIA, args.scores, strict=True))})  # fmt: skip
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    done = sorted({e["output"] for e in data["entries"]})
    print(
        f"{args.by}: {args.output} recorded {args.scores}; scored so far: {', '.join(done)}; "
        f"still to score: {', '.join(o for o in OUTPUTS if o not in done) or 'none'}"
    )


if __name__ == "__main__":
    main()
