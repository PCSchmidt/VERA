"""Every requirement due by the current increment and verified by test (T) has a test.

A requirement row in docs/02 is due when the first increment in its `Incr`
cell is <= the current increment (from SPEC.md). Its test must be named
`test_<ID>_...` with dashes as underscores, e.g. `test_FND_C_02_hash_matches`.
This catches omissions: a requirement nobody tested.
"""

from __future__ import annotations

import re
from pathlib import Path

from _common import block, current_increment, ok, repo_root_arg

ROW = re.compile(r"^\|\s*([A-Z]{3}-[FPC]-\d{2})\s*\|")


def due_test_requirements(requirements: Path, increment: int) -> list[str]:
    due = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        verify, incr = cells[2], cells[3]
        first_incr = re.match(r"\d+", incr)
        if first_incr is None:
            continue
        if re.search(r"\bT\b", verify) and int(first_incr.group()) <= increment:
            due.append(match.group(1))
    return due


def test_names(root: Path) -> set[str]:
    names: set[str] = set()
    tests = root / "tests"
    if not tests.exists():
        return names
    for path in tests.rglob("test_*.py"):
        names.update(re.findall(r"^\s*(?:async\s+)?def\s+(test_\w+)", path.read_text(encoding="utf-8"), re.MULTILINE))
    return names


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    requirements = args.root / "docs" / "02-requirements.md"
    if not requirements.exists():
        block(f"{requirements} not found")
    increment = current_increment(args.root)
    due = due_test_requirements(requirements, increment)
    names = test_names(args.root)
    def tested(req: str) -> bool:
        stem = f"test_{req.replace('-', '_')}"
        return any(name == stem or name.startswith(f"{stem}_") for name in names)

    missing = [req for req in due if not tested(req)]
    if missing:
        block(f"increment {increment}: no test for {', '.join(missing)} (name tests test_<ID>_...)")
    ok(f"increment {increment}: all {len(due)} test-verified requirement(s) due have tests")


if __name__ == "__main__":
    main()
