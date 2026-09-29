"""Gate `confirmed`: the monthly spend ceiling in ConOps §4 is a dollar amount, not TBD."""

from __future__ import annotations

import re

from _common import block, ok, repo_root_arg


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    conops = args.root / "docs" / "01-conops.md"
    if not conops.exists():
        block(f"{conops} not found")
    line = next(
        (text for text in conops.read_text(encoding="utf-8").splitlines() if "spend ceiling" in text.lower()),
        None,
    )
    if line is None:
        block("docs/01-conops.md has no 'Monthly spend ceiling' line")
    if "TBD" in line.upper() or not re.search(r"\$\s?\d", line):
        block(f"spend ceiling is not set to a dollar amount: {line.strip()}")
    ok(f"spend ceiling set: {line.strip()}")


if __name__ == "__main__":
    main()
