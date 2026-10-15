# ruff: noqa: E501
"""The project's total model spend, from every ledger file in the repository (no model call).

Sums `cost_usd` over every record in `data/ledger/*.jsonl` and every run ledger copied into `data/**/ledger.jsonl` (a review
or paper's evidence folder keeps a copy of its run's ledger), counting each record once by its `trace_id` (a copy repeats
records already in `data/ledger/`). Two runs' ledgers exist only as copies (the app rehearsal and the new-user walkthrough),
which is why the copies are read at all. Writes `data/results/spend_total.json` with the total, the files read and what each
added. Note: `data/ledger/` is git-ignored except for named result ledgers, so the figure is reproducible on the machine
that ran the work; the per-increment totals are in each review.

    uv run python scripts/spend_total.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    files = sorted((ROOT / "data" / "ledger").glob("*.jsonl")) + sorted((ROOT / "data").glob("**/ledger.jsonl"))
    seen: set[str] = set()
    added: dict[str, float] = defaultdict(float)
    records = duplicates = 0
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            r = json.loads(line)
            key = r.get("trace_id") or f"{f}:{n}"
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            records += 1
            added[f.relative_to(ROOT).as_posix()] += r.get("cost_usd") or 0.0
    total = sum(added.values())
    in_ledger_dir = sum(v for k, v in added.items() if k.startswith("data/ledger/"))
    out = {"computed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "total_usd": round(total, 4),
           "data_ledger_usd": round(in_ledger_dir, 4), "files_read": len(files), "records": records,
           "duplicates_skipped": duplicates,
           "only_in_copies": {k: round(v, 4) for k, v in added.items() if not k.startswith("data/ledger/") and v > 0}}  # fmt: skip
    (ROOT / "data" / "results" / "spend_total.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
