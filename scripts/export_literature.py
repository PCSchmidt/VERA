"""Copy each topic's finished literature section and its claims into data/literature/<id>/ (committed evidence).

The run directories under runs/ are git-ignored; the section, its claims (source key, quote, locator) and the synthesis
statistics are what the Increment 3 review and `check_literature.py` read. Passages are not copied: they are excerpts of
other people's papers beyond the short quotes the claims carry.

Usage: uv run python scripts/export_literature.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    topics = json.loads((ROOT / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    for tid in topics:
        scope = json.loads((ROOT / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run = ROOT / "runs" / scope["run_id"]
        dest = ROOT / "data" / "literature" / tid
        dest.mkdir(parents=True, exist_ok=True)
        for name, src in (("literature.md", run / "literature.md"), ("claims.jsonl", run / "claims.jsonl"),
                          ("literature.json", run / "artifacts" / "literature.json")):  # fmt: skip
            shutil.copy(src, dest / name)
        for name, src in (("audit.md", run / "audit.md"),
                          ("audit_repair.json", run / "artifacts" / "audit_repair.json"),
                          ("literature.pre_audit_repair.md", run / "literature.pre_audit_repair.md"),
                          ("claims.pre_audit_repair.jsonl", run / "claims.pre_audit_repair.jsonl"),
                          ("parent.json", run / "parent.json")):  # fmt: skip
            if src.exists():  # present once the final audit (and, if it failed claims, the repair) have run
                shutil.copy(src, dest / name)
        print(f"{tid}: exported from {run.name}")


if __name__ == "__main__":
    main()
