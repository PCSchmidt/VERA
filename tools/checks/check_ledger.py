"""A run ledger is complete and inside its budget (gate backends_live; FND-F-01, JDG-F-04 demonstration).

Blocks unless the ledger (default data/ledger/smoke.jsonl):
- is JSON lines, every line a LedgerRecord with every field present (docs/03);
- has successful calls (no `error`) from at least --min-backends backends;
- records, for every successful call, token counts, latency and a trace id,
  and a cost > 0 (every candidate backend is paid; --free names exceptions);
- totals no more than --max-usd.
Failed calls are allowed (the ledger must record them) and are counted.
"""

from __future__ import annotations

import json
from pathlib import Path

from _common import block, ok, repo_root_arg

FIELDS = ["trace_id", "run_id", "component", "backend", "model", "input_tokens", "output_tokens", "cost_usd",
          "latency_ms", "timestamp", "error"]  # fmt: skip


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("data/ledger/smoke.jsonl"), help="repo-relative")
    parser.add_argument("--max-usd", type=float, default=1.00)
    parser.add_argument("--min-backends", type=int, default=2)
    parser.add_argument("--free", nargs="*", default=[], help="backends allowed a zero cost (e.g. a local model)")
    args = parser.parse_args()
    path = args.root / args.ledger
    if not path.exists():
        block(f"{args.ledger.as_posix()} not found")

    records = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            block(f"line {n}: not JSON")
        missing = [f for f in FIELDS if f not in rec]
        if missing:
            block(f"line {n}: missing fields {missing}")
        records.append((n, rec))
    if not records:
        block("the ledger is empty")

    good = [(n, r) for n, r in records if r["error"] is None]
    for n, r in good:
        for f in ("input_tokens", "output_tokens", "latency_ms"):
            if not isinstance(r[f], int) or isinstance(r[f], bool) or r[f] < 0:
                block(f"line {n} ({r['backend']}): {f} is {r[f]!r}, not a count")
        if not r["trace_id"] or not r["model"] or not r["timestamp"]:
            block(f"line {n} ({r['backend']}): empty trace_id, model or timestamp")
        if r["backend"] not in args.free and not (isinstance(r["cost_usd"], (int, float)) and r["cost_usd"] > 0):
            block(f"line {n} ({r['backend']}): cost {r['cost_usd']!r} for a paid backend")
    backends = sorted({r["backend"] for _, r in good})
    if len(backends) < args.min_backends:
        block(f"successful calls from {len(backends)} backend(s) {backends}; need {args.min_backends}")
    total = sum(float(r["cost_usd"]) for _, r in records)
    if total > args.max_usd:
        block(f"ledger total ${total:.4f} exceeds ${args.max_usd:.2f}")

    ok(
        f"{len(records)} calls ({len(records) - len(good)} failed) from {len(backends)} backends {backends}; "
        f"total ${total:.4f} <= ${args.max_usd:.2f}"
    )


if __name__ == "__main__":
    main()
