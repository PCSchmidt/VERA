"""Gate `scoping_ready`: each topic was scoped live, shown to the user, confirmed or edited, within the scoping cap.

For every topic in data/topics/manifest.json, data/topics/scope_<id>.json (written by
scripts/confirm_scope.py --copy-to) must hold a confirmed or edited question with who and when, and the run it came
from. That run's ledger data/ledger/run_<run_id>.jsonl must show that, up to the moment of confirmation, the run
made only scoping calls (p3.scope and the judge path) and spent at most the cap ($0.25 by default): nothing beyond
scoping before the user confirmed (RSH-F-08). The check reports how many questions the user edited.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

SCOPING_COMPONENTS = {"p3.scope", "p2.cheap_path", "p2.judge"}


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=0.25)
    args = parser.parse_args()
    manifest_file = args.root / "data" / "topics" / "manifest.json"
    if not manifest_file.exists():
        block("data/topics/manifest.json not found")
    topics = json.loads(manifest_file.read_text(encoding="utf-8"))["topics"]
    edited = 0
    for tid in topics:
        scope_file = args.root / "data" / "topics" / f"scope_{tid}.json"
        if not scope_file.exists():
            block(f"{scope_file.name} not found: scope the topic and confirm it (scripts/confirm_scope.py --copy-to)")
        scoped = json.loads(scope_file.read_text(encoding="utf-8"))
        who = scoped.get("confirmed_by") and scoped.get("confirmed_at")
        if scoped.get("status") not in ("confirmed", "edited") or not who:
            block(f"{tid}: the scoped question is not confirmed by a named person with a time")
        edited += scoped["status"] == "edited"
        ledger = args.root / "data" / "ledger" / f"run_{scoped.get('run_id')}.jsonl"
        if not ledger.exists():
            block(f"{tid}: ledger of run {scoped.get('run_id')!r} not found")
        records = [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
        before = [r for r in records if r["timestamp"] <= scoped["confirmed_at"]]
        stray = sorted({r["component"] for r in before} - SCOPING_COMPONENTS)
        if stray or not any(r["component"] == "p3.scope" for r in before):
            block(f"{tid}: before the confirmation the run made calls other than scoping ({stray}) or none at all")
        spent = sum(r["cost_usd"] for r in before)
        if spent > args.cap_usd + 1e-9:
            block(f"{tid}: ${spent:.4f} spent on scoping before the confirmation, over the ${args.cap_usd} cap")
    ok(f"{len(topics)} topics scoped and confirmed within the cap; {edited} of {len(topics)} edited by the user")


if __name__ == "__main__":
    main()
