# ruff: noqa: E501
"""Freeze the audit v3's source hash in both the seeded-set and the novelty gold-set splits (Increment 4, audit4_ready).

One freeze covers both test runs: after it, any change to a file in `vera.audit.seeded_v3.FROZEN_FILES` spends both test sets.
Refuses if either split is already frozen. Run it once, after the audit is developed on the dev splits and before either test run.

Usage: uv run python scripts/freeze_audit_v3.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from vera.audit import seeded_v3

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    files = [ROOT / "data" / "seeded_v3" / "split.json", ROOT / "data" / "novelty_gold" / "split.json"]
    splits = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    if any(s.get("frozen_audit_sha256") for s in splits):
        raise SystemExit("already frozen")
    digest = seeded_v3.audit_source_sha256(ROOT)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for f, s in zip(files, splits, strict=True):
        f.write_text(json.dumps(s | {"frozen_audit_sha256": digest, "frozen_at": stamp}, indent=1), encoding="utf-8")
    print(f"audit v3 frozen {stamp}: {digest[:16]} (both test runs need exactly this source)")


if __name__ == "__main__":
    main()
