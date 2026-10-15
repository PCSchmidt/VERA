# ruff: noqa: E501
"""Increment 10 (close-out) checks, by part (SPEC.md). Exit 0 passes, exit 2 blocks.

--part sticky  (gate `sticky_answer_ready`): the audit's asker looks up the reference's stored write-time answer before
               asking again, in both audits; the offline re-read of the Increment 9 papers is recorded; RSH-F-17 tests grew;
               the earlier freezes hold.
--part docs    (gate `closeout_docs_ready`): the README states what each colour of the light means and what none means;
               the retrospective exists with its sections; docs/07 marks the work closed and lists what is not planned.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _common import block, ok, repo_root_arg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_carry6 import has_tests  # noqa: E402
from check_carry9 import freezes  # noqa: E402

RETRO_SECTIONS = ("## What was built", "## What was measured", "## What was never shown", "## Spend", "## The process",
                  "## Why the work stopped here")  # fmt: skip


def part_sticky(root: Path) -> None:
    if not (root / "vera" / "audit" / "sticky.py").exists():
        block("vera/audit/sticky.py not found")
    pipeline = (root / "vera" / "app" / "pipeline.py").read_text(encoding="utf-8")
    if "sticky.lookup(" not in pipeline or pipeline.count("sticky.index(") < 2:
        block("both audits must look up the stored write-time reference answer")
    path = root / "data" / "results" / "sticky10.json"
    if not path.exists():
        block("no offline re-read of the Increment 9 papers (scripts/reread10.py)")
    papers = json.loads(path.read_text(encoding="utf-8"))["papers"]
    n = has_tests(root, "RSH-F-17", 10)
    moved = {k: [m["item"] for m in v["moved"]] for k, v in papers.items()}
    ok(f"the write-time reference answer sticks in both audits; re-read moved {moved}; {n} RSH-F-17 tests; {freezes(root)}")


def part_docs(root: Path) -> None:
    readme = (root / "README.md").read_text(encoding="utf-8")
    if "What the audit light means" not in readme:
        block("the README has no section 'What the audit light means'")
    section = readme.split("What the audit light means", 1)[1].split("\n## ", 1)[0]
    for word in ("Green", "Amber", "Red", "unsettled", "disagree", "does not mean"):
        if word.lower() not in section.lower():
            block(f"the README's light section does not cover {word!r}")
    retro = root / "docs" / "reviews" / "retrospective.md"
    if not retro.exists():
        block("docs/reviews/retrospective.md not found")
    text = retro.read_text(encoding="utf-8")
    missing = [s for s in RETRO_SECTIONS if s not in text]
    if missing:
        block(f"the retrospective lacks {missing}")
    plan = (root / "docs" / "07-increments.md").read_text(encoding="utf-8")
    if "Not planned" not in plan or "closed" not in plan.lower():
        block("docs/07 does not mark the plan closed with its not-planned list")
    ok("README light section, retrospective and closed plan present")


PARTS = {"sticky": part_sticky, "docs": part_docs}


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--part", choices=sorted(PARTS), required=True)
    args = parser.parse_args()
    PARTS[args.part](args.root)


if __name__ == "__main__":
    main()
