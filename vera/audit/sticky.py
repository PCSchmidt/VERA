# ruff: noqa: E501
"""The reference's write-time answer sticks in the audit (RSH-F-17, completed in Increment 10).

Since Increment 9 the write step asks the reference judge to confirm a cheap "no" and stores its verdict on the sentence or
statement. The audit used to ask the reference again on the same text and let the second answer decide, so an unsure
write-time no (0.62) became a confident audit no (0.80) and a failure, and an unsure no became an unsure yes, on unchanged
text (Increment 9's N1, C41 and S60). Here the audit looks up the stored answer first: same question, same item text, and it
uses that answer instead of asking again. An item whose text changed, or that has no stored reference verdict, is confirmed
in the audit as before.

The judge's material quotes the item's own text (`Claim: <sentence>` for `claim.within_quote`, `Statement: <text>` for
`paper.inference_follows`), so the item is found from the material without the audit needing to know which record it came
from. `vera/audit/sentences.py` and `sentence_checks.py` are not edited (hashed for Increment 7).
"""

from __future__ import annotations

import re

from vera.schemas import Verdict

REFERENCE = "sonnet-ref"
_PREMISES = re.compile(r"\s*\((?:C\d+)(?:,\s*C\d+)*\)")


def _key_text(text: str) -> str:
    return " ".join(_PREMISES.sub("", text).split())


def index(records: list[dict]) -> dict[tuple[str, str], Verdict]:
    """(question id, item text) -> the last reference verdict stored on that item at write time."""
    out: dict[tuple[str, str], Verdict] = {}
    for r in records:
        for v in r.get("verdicts") or []:
            if v.get("backend") == REFERENCE:
                out[(v["question_id"], _key_text(r["text"]))] = Verdict.model_validate(v)
    return out


def item_text(question_id: str, material: str) -> str | None:
    """The item's own text, read back from the judge's material, or None if the material has no recognisable item."""
    if question_id == "claim.within_quote":
        m = re.search(r"Claim: (.*?)\n\nQuote from that source:", material, re.S)
    elif question_id == "paper.inference_follows":
        m = re.search(r"\nStatement: (.*)\Z", material, re.S)
    else:
        return None
    return _key_text(m.group(1)) if m else None


def lookup(stored: dict[tuple[str, str], Verdict], question_id: str, material: str) -> Verdict | None:
    text = item_text(question_id, material)
    return stored.get((question_id, text)) if text is not None else None
