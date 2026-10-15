"""The write step confirms a cheap judge's "no" with the reference judge (RSH-F-17, Increment 9).

Since Increment 8 the audit asks the reference judge (Claude Sonnet 5.5) to confirm a cheap "no" on the questions in
`cheap_path.CONFIRM_NO`. Asking it only in the audit meant the writer never repaired what the reference rejects, and
removed what it would accept. Here the write step asks it at the same point:

- the reference's confident yes: the sentence or statement is kept, with no repair; both verdicts are stored;
- its confident no: the item goes to repair as before;
- an answer below the threshold: kept, stored as unsettled (the audit reports it so).

The reference is `deps.extra["reference"]`, a judge backend on the run's ledger and budget; with none (tests, or a run
without it) nothing changes. The producer of the text never judges it: the reference is a judge, as the cheap path is.
"""

from __future__ import annotations

from vera.judge.cheap_path import CONFIRM_NO
from vera.schemas import Question, Verdict

UNSETTLED_AT_WRITE = "unsettled at write time: the reference judge was unsure"


def enabled(deps) -> bool:
    return deps.extra.get("reference") is not None


def confirm_no(deps, question: Question, material: str, producer: str) -> tuple[str, list[Verdict]]:
    """("keep" | "fail" | "unsettled", the reference's verdicts) for a confident cheap "no" on `question`. A question
    the reference does not confirm, or no reference, is "fail" with no verdict: the cheap judge's no stands."""
    reference = deps.extra.get("reference")
    if reference is None or question.id not in CONFIRM_NO:
        return "fail", []
    (v,) = reference.ask(material, [question])
    v = v.model_copy(update={"producer_id": producer})
    confident = v.confidence_source != "none" and v.confidence >= deps.min_confidence
    if not confident:
        return "unsettled", [v]
    return ("keep" if v.answer is True else "fail"), [v]
