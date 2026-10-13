# ruff: noqa: E501
"""Record rubric scores for one Increment 7 paper (SPEC "Rubric scoring of the new papers"; docs/results/rubric_sheet_7.md).

Two papers: N1, P2's paper made again (`data/paper_rerun/discuss-the-evolution-of-prompting-guv8`), and N2, the new paper
(`data/paper_rerun/rlm-vs-clm-2`). Each is scored 1 to 5 on the Increment 6 rubric's six criteria and given a preference
against the review it came from (paper, review or same). The first scorer's scores go to data/results/rubric7_first.json
with the scorer's real name in `--by`; the independent scorer's to rubric7_evaluator.json with `--defects`.

`--blind`: the scorer has not read the other scorer's scores (refused once the independent file exists, except for the
independent scorer). `--attribution`: required when the first scorer is not Chris, saying who scored and at whose request.
`--defects` (independent scorer): a JSON list of {"id": "C12" or "S40" or "I3", "kind": "...", "note": "..."}.

Usage: uv run python scripts/record_rubric7.py N1 --by "<name>" --blind 3 3 3 4 4 3 --prefer paper --note "why" [--attribution "..."]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ("N1", "N2")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty", "interpretation_follows")
INDEPENDENT = "evaluator"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", choices=OUTPUTS)
    ap.add_argument("scores", type=int, nargs=len(CRITERIA), help="1-5 for each criterion, in the documented order")
    ap.add_argument("--by", required=True, help="who is scoring: a real name, or 'evaluator' for the independent scorer")
    ap.add_argument("--blind", action="store_true", help="I have not read the other scorer's scores")
    ap.add_argument("--prefer", required=True, choices=("paper", "review", "same"))
    ap.add_argument("--note", default="")
    ap.add_argument("--attribution", default="", help="who actually scored, and at whose request, when it is not Chris")
    ap.add_argument("--defects", default="", help="independent scorer: JSON list of defects by claim, sentence or statement id")
    args = ap.parse_args()
    if not all(1 <= s <= 5 for s in args.scores):
        raise SystemExit("each score is 1 to 5")
    results = ROOT / "data" / "results"
    independent = args.by.lower() == INDEPENDENT
    if args.blind and not independent and (results / f"rubric7_{INDEPENDENT}.json").exists():
        raise SystemExit("the independent scorer's file already exists: scores given now cannot be marked blind")
    if not independent and args.by != "Chris" and not args.attribution.strip():
        raise SystemExit("--attribution is required when the first scorer is not Chris")
    defects = json.loads(args.defects) if args.defects.strip() else []
    if independent and not isinstance(defects, list):
        raise SystemExit("--defects must be a JSON list")
    path = results / ("rubric7_evaluator.json" if independent else "rubric7_first.json")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"by": args.by, "entries": []}
    if data["by"] != args.by:
        raise SystemExit(f"{path.name} is {data['by']}'s file")
    if args.attribution.strip():
        data["attribution"] = args.attribution.strip()
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {"output": args.output, "at": stamp, "blind": bool(args.blind), "prefer": args.prefer, "note": args.note,
             "scores": dict(zip(CRITERIA, args.scores, strict=True))}  # fmt: skip
    if independent:
        entry["defects"] = defects
    data["entries"].append(entry)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    done = sorted({e["output"] for e in data["entries"]})
    print(f"{args.by}: {args.output} recorded {args.scores}, prefers {args.prefer} (blind: {args.blind}); "
          f"still to score: {', '.join(o for o in OUTPUTS if o not in done) or 'none'}")  # fmt: skip


if __name__ == "__main__":
    main()
