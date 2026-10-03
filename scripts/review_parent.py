"""Copy a topic run's parent-problem selection to data/topics/parent_<topic>.json, and record the user's reading of it.

Without --right/--wrong it copies the selection (user_review stays empty) and prints the evidence: the candidates with
their live checks and the reasons for a pick or a refusal. The user reads it and records whether the pick, or the
refusal, was right (RSH-F-10 acceptance); the review is kept in the file, with who and when, never edited by the agent.

Usage:
  uv run python scripts/review_parent.py scope-tree-explain-2
  uv run python scripts/review_parent.py scope-tree-explain-2 --by Chris --right --note "TreeHFD is the one"
  uv run python scripts/review_parent.py scope-credal-dro-2 --by Chris --wrong --note "E2E-DRO has public data"
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from vera.schemas import ParentSelection

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    ap.add_argument("--by", help="who is recording the reading (required with --right/--wrong)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--right", action="store_true", help="the pick (or the refusal) was right")
    group.add_argument("--wrong", action="store_true", help="the pick (or the refusal) was wrong")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    source = ROOT / "runs" / args.run_id / "parent.json"
    selection = ParentSelection.model_validate_json(source.read_text(encoding="utf-8"))
    target = ROOT / "data" / "topics" / f"parent_{selection.topic_id}.json"
    if target.exists():  # keep an earlier reading when the selection has not changed
        earlier = ParentSelection.model_validate_json(target.read_text(encoding="utf-8"))
        if earlier.user_review and earlier.model_copy(update={"user_review": None}) == selection:
            selection = selection.model_copy(update={"user_review": earlier.user_review})
    if args.right or args.wrong:
        if not args.by:
            raise SystemExit("--by is required: the reading is the user's, with a name")
        stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        review = {"right": bool(args.right), "note": args.note, "by": args.by, "at": stamp}
        selection = selection.model_copy(update={"user_review": review})
    target.write_text(selection.model_dump_json(indent=1), encoding="utf-8")
    print(f"topic {selection.topic_id}: question: {selection.question}")
    print("picked:" if selection.picked else "refused:", selection.picked or selection.none_fits_reason)
    for c in selection.candidates:
        print(f"\n- {c.repo_url}  (paper {c.paper_id}: {c.title})")
        print(f"  resolves={c.repo_resolves} licence={c.licence} own_code={c.own_code} archived={c.archived}")
        print(f"  datasets={c.datasets} compute[{c.compute_basis}]={c.compute!r} cpu_minutes={c.cpu_minutes}")
        print(f"  harness={c.harness_in_docker}; paper says: {c.url_context[:200]!r}")
    print("\njudge:", [(v.question_id, v.answer, v.confidence) for v in selection.verdicts])
    print("your reading:", selection.user_review or "(none recorded)")
    print(f"written: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
