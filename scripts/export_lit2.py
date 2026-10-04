"""Copy finished literature runs of Increment 4 into committed evidence folders (the runs/ directories are git-ignored).

Each argument is `<run id>:<destination under data/>`, e.g. `topic4-agents-resynth:literature/research-agents-eval`.
Copies the section, its claims, the synthesis statistics, the audit and (when present) the repair record, parent
selection and scope; passages are not copied (excerpts of other people's papers beyond the claims' short quotes).

Usage: uv run python scripts/export_lit2.py topic4-agents-resynth:literature/research-agents-eval ...
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "literature.md", "claims.jsonl", "audit.md", "parent.json", "scope.json", "literature.pre_audit_repair.md",
    "claims.pre_audit_repair.jsonl", "artifacts/literature.json", "artifacts/audit_report.json",
    "artifacts/audit_repair.json", "artifacts/parent_candidates.json", "artifacts/queries.json",
    "artifacts/relevance.json", "artifacts/reading.json",
)  # fmt: skip


def main() -> None:
    for arg in sys.argv[1:]:
        run_id, dest = arg.split(":", 1)
        run, out = ROOT / "runs" / run_id, ROOT / "data" / dest
        out.mkdir(parents=True, exist_ok=True)
        copied = []
        for name in FILES:
            if (run / name).exists():
                shutil.copy(run / name, out / Path(name).name)
                copied.append(Path(name).name)
        print(f"{run_id} -> data/{dest}: {len(copied)} files")


if __name__ == "__main__":
    main()
