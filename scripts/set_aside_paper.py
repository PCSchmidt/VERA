"""Move a review's finished paper aside so the app can make the paper again (Increment 7, `paper_rerun`).

    uv run python scripts/set_aside_paper.py <run_id>

The app makes one paper per review (`runs/<run_id>/paper/`). To make P2's paper again with the Increment 7 checks, the
Increment 6 paper is moved to `runs/<run_id>/paper_incr6/` (nothing is deleted; its copy is also in `data/paper_demo/`).
Refuses while a paper is being made, or if a set-aside paper is already there.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run = ROOT / "runs" / sys.argv[1]
    paper, aside = run / "paper", run / "paper_incr6"
    if not paper.exists():
        sys.exit(f"{paper} does not exist")
    if aside.exists():
        sys.exit(f"{aside} already exists; nothing moved")
    state_file = paper / "app_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8")).get("state") if state_file.exists() else None
    if state in {"queued", "running", "stopping"}:
        sys.exit(f"a paper is being made ({state}); stop it first")
    shutil.move(str(paper), str(aside))
    print(f"moved {paper.relative_to(ROOT)} to {aside.relative_to(ROOT)}; the app can make this paper again")


if __name__ == "__main__":
    main()
