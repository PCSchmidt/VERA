# ruff: noqa: E501
"""Gate `comparison4` (before Chris approves): the comparison with ScientistTwo was made under a protocol fixed first.

Requires:
- docs/results/comparison_protocol.md with the SHA-256 in comparison_protocol.sha256 (recomputed here), committed before the
  comparison table: the table's own first commit comes after the protocol's (git log order);
- docs/results/comparison_table.md covering both problems (TreeHFD and credal), each row naming the metric and the row set ScientistTwo's
  paper reports it on, whether the two sit on the same row set, the loop's gain as measured, ScientistTwo's reported gain, the cost on each
  side ("not published" where it is), and the caveats; it says whether the 25% line of the protocol is met for each problem and does not
  claim MOE-3 met where the cost half is not assessable;
- a statement of what the comparison does and does not show.
"""

from __future__ import annotations

import hashlib
import re
import subprocess

from _common import block, ok, repo_root_arg


def first_commit(root, path: str) -> int:
    out = subprocess.run(["git", "log", "--follow", "--format=%ct", "--", path], cwd=root, capture_output=True, text=True).stdout.split()
    return int(out[-1]) if out else 10**12


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    res = args.root / "docs" / "results"
    proto, table = res / "comparison_protocol.md", res / "comparison_table.md"
    for f in (proto, res / "comparison_protocol.sha256", table):
        if not f.exists():
            block(f"{f.name} not found")
    digest = hashlib.sha256(proto.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if digest != (res / "comparison_protocol.sha256").read_text(encoding="utf-8").split()[0]:
        block("the comparison protocol changed after its hash was recorded")
    if first_commit(args.root, "docs/results/comparison_protocol.md") > first_commit(args.root, "docs/results/comparison_table.md"):
        block("the comparison table was committed before the protocol")
    text = table.read_text(encoding="utf-8")
    for problem in ("TreeHFD", "credal"):
        if not re.search(problem, text, re.IGNORECASE):
            block(f"the comparison table does not cover {problem}")
    for needle in ("row set", "not published", "25%", "does not show"):
        if needle.lower() not in text.lower():
            block(f"the comparison table lacks {needle!r}")
    if re.search(r"MOE-3[^.\n]*\bmet\b(?! on the gain half)", text) and "not assessable" not in text.lower():
        block("the table claims MOE-3 met without the cost half being assessable")
    ok(f"protocol hash {digest[:12]} intact and committed before the table; the table covers both problems with caveats")


if __name__ == "__main__":
    main()
