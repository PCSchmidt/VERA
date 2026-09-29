"""A trade study in docs/04 is decided: heading no longer 'open', with scores, a decision, and a reversal condition.

Usage: check_trade_decided.py T3
"""

from __future__ import annotations

import re

from _common import block, ok, repo_root_arg


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("trade", help="trade id, e.g. T3")
    args = parser.parse_args()
    doc = args.root / "docs" / "04-trade-studies.md"
    if not doc.exists():
        block(f"{doc} not found")
    text = doc.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(args.trade)}\b.*$", text, re.MULTILINE)
    if not match:
        block(f"no '## {args.trade}' section in docs/04-trade-studies.md")
    heading = match.group(0)
    next_heading = re.search(r"^## ", text[match.end():], re.MULTILINE)
    section = text[match.end(): match.end() + next_heading.start()] if next_heading else text[match.end():]

    if re.search(r"\bopen\b", heading, re.IGNORECASE):
        block(f"{args.trade} is still open: {heading.strip()}")
    if not re.search(r"\*\*Decision:?\*\*", section):
        block(f"{args.trade} has no **Decision:** line")
    if not re.search(r"\*\*Reverse if:?\*\*", section):
        block(f"{args.trade} has no **Reverse if:** line")
    if not re.search(r"\*\*Scores:?\*\*", section):
        block(f"{args.trade} has no **Scores:** line (the measured comparison behind the decision)")
    ok(f"{args.trade} decided: {heading.strip()}")


if __name__ == "__main__":
    main()
