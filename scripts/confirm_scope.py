"""Confirm (or edit) the scoped question a topic run proposed, so the run can continue (RSH-F-08).

A topic run stops after scoping and spends nothing more until the question is confirmed. This records who confirmed
it and when in runs/<run_id>/scope.json, and, with --copy-to, a committed copy for the review.

Usage:
  uv run python scripts/confirm_scope.py <run_id> --show
  uv run python scripts/confirm_scope.py <run_id> --by Chris --accept
  uv run python scripts/confirm_scope.py <run_id> --by Chris --edit "A more specific question?"
  uv run python scripts/confirm_scope.py <run_id> --by Chris --accept --copy-to data/topics/scope_<topic>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vera.literature import scoping

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    ap.add_argument("--show", action="store_true", help="print the proposal and exit")
    ap.add_argument("--by", help="who confirms (required to accept or edit)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--accept", action="store_true")
    group.add_argument("--edit", metavar="QUESTION", help="replace the question with this one")
    ap.add_argument("--copy-to", type=Path, help="also write a copy of the confirmed record here")
    args = ap.parse_args()

    run_dir = ROOT / "runs" / args.run_id
    scoped = scoping.read_scope(run_dir)
    if scoped is None:
        sys.exit(f"no scoped question in {run_dir}: the run has not proposed one")
    print(json.dumps(scoped.model_dump(mode="json"), indent=1))
    if args.show or not (args.accept or args.edit):
        return
    if not args.by:
        sys.exit("--by <name> is required: the record says who confirmed")
    confirmed = scoping.confirm_scope(run_dir, args.by, question=args.edit)
    print(f"\nrecorded: {confirmed.status} by {confirmed.confirmed_by} at {confirmed.confirmed_at}")
    if args.copy_to:
        target = args.copy_to if args.copy_to.is_absolute() else ROOT / args.copy_to
        target.parent.mkdir(parents=True, exist_ok=True)
        record = confirmed.model_dump(mode="json") | {"run_id": args.run_id}  # which run's ledger holds its cost
        target.write_text(json.dumps(record, indent=1), encoding="utf-8")
        print(f"copy: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
