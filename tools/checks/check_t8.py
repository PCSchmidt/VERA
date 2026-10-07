"""Gate `t8_decided`: the T8 entry in docs/04 has measured costs, Scores, Decision and Reverse if."""

from __future__ import annotations

import re

from _common import block, ok, repo_root_arg


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    text = (args.root / "docs" / "04-trade-studies.md").read_text(encoding="utf-8")
    m = re.search(r"^## T8 .*?(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        block("docs/04 has no T8 section")
    t8 = m.group(0)
    for need in ("Measured before the decision", "**Scores:**", "**Decision:**", "Reverse if"):
        if need not in t8:
            block(f"the T8 entry lacks {need!r}")
    if "(open" in t8.splitlines()[0]:
        block("the T8 heading still says open")
    for ledger_hint in ("data/ledger/run_topic4-", "docs/results/runs4.json"):
        if ledger_hint not in t8:
            block(f"the T8 costs do not name their source ({ledger_hint})")
    ok("T8 entry has measured costs with sources, scores, a decision and reverse-if")


if __name__ == "__main__":
    main()
