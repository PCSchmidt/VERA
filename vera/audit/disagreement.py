# ruff: noqa: E501
"""Judge disagreement is not failure (AUD-F-13, Increment 8); an unsure judge is not a verdict (AUD-F-14, Increment 9).

Increment 7's two papers were red only where the judge disagreed with itself: a sentence passed a question when it was
written and failed the same question in the audit. A red light should mean the judge of record said no. This module
takes the audit's sentence and inference findings and, where the finding rests on a judge verdict that contradicts the
verdict recorded when the text was written, turns the `fail` into a `warn` that says so:

- a finding is downgraded only when its audit verdict is a confident no **and** the last write-time verdict on the same
  question for the same sentence or statement was a confident yes;
- a failure from a rule (no verdict), a write-time no that was repaired and failed again, and anything in a document
  made before sentence statuses (no write-time verdicts) stay failures.

`vera/audit/sentences.py` is not edited (it is hashed for Increment 7's real-case measurement); the app's pipeline applies
this to the findings it returns.
"""

from __future__ import annotations

from vera.schemas import Finding

PREFIX = "judges disagree"
MIN_CONFIDENCE = 0.7


def _confident(v: dict | object, answer: bool) -> bool:
    get = v.get if isinstance(v, dict) else lambda k, d=None: getattr(v, k, d)
    return get("answer") is answer and (get("confidence") or 0.0) >= MIN_CONFIDENCE


def _last(verdicts: list, question_id: str) -> dict | object | None:
    get = lambda v, k: v.get(k) if isinstance(v, dict) else getattr(v, k, None)  # noqa: E731
    return next((v for v in reversed(verdicts) if get(v, "question_id") == question_id), None)


def _describe(v: dict | object) -> str:
    get = v.get if isinstance(v, dict) else lambda k, d=None: getattr(v, k, d)
    return f"{'yes' if get('answer') is True else 'no'} on {get('backend')} at {get('confidence') or 0:.2f}"


def outcome(audit_v, ref, before) -> tuple[str, str | None]:
    """The judge of record's outcome for a judge failure (AUD-F-13, AUD-F-14): ("fail" | "disagree" | "unsettled", why).

    - The reference was asked (`ref`): its confident yes makes a disagreement, its confident no a failure, and an answer
      below the threshold either way leaves the item unsettled.
    - Otherwise a confident write-time yes on the same question (`before`, which may itself be the reference's, RSH-F-17)
      against the audit's confident no makes a disagreement; anything else is the cheap judge's failure.
    """
    if ref is not None:
        if _confident(ref, True):
            return "disagree", f"failed in the audit, {_describe(audit_v)}; the reference judge says yes, {_describe(ref)}"
        if _confident(ref, False):
            return "fail", None
        return "unsettled", f"the reference judge was unsure ({_describe(ref)}; the audit's judge said {_describe(audit_v)})"
    if before is not None and _confident(before, True) and _confident(audit_v, False):
        return "disagree", f"passed at write time, {_describe(before)}; failed in the audit, {_describe(audit_v)}"
    return "fail", None


UNSETTLED = "unsettled"


def reconcile(
    findings: list[Finding], sentences: list[dict], inferences: list[dict], confirmations: dict[str, object] | None = None
) -> tuple[list[Finding], int]:
    """(findings with each judge failure settled by `outcome`, how many became disagreements). `sentences` and
    `inferences` are the document's stored records (dumps), whose `verdicts` are the write-time verdicts. `confirmations`
    maps the trace id of an audit "no" to the reference judge's verdict on the same question and material
    (`cheap_path.CONFIRM_NO`). A disagreement or an unsettled item becomes a warning that says so; a failure stands, with
    the reference's verdict on record when it was asked. Rule failures (no verdict) are left alone."""
    written = {s["id"]: s.get("verdicts") or [] for s in sentences} | {i["id"]: i.get("verdicts") or [] for i in inferences}
    confirmations = confirmations or {}
    out, n = [], 0
    for f in findings:
        if f.severity != "fail" or f.check not in ("sentence", "inference") or not f.verdicts:
            out.append(f)
            continue
        key = f.evidence[0].claim_id if f.evidence else (f.claim_ids[0] if f.claim_ids else None)
        audit_v = f.verdicts[-1]
        ref = confirmations.get(audit_v.trace_id)
        before = _last(written.get(key, []), audit_v.question_id)
        kind, why = outcome(audit_v, ref, before)
        verdicts = [*f.verdicts, ref] if ref is not None else f.verdicts
        if kind == "fail":
            out.append(f.model_copy(update={"verdicts": verdicts}))
            continue
        n += kind == "disagree"
        prefix = PREFIX if kind == "disagree" else UNSETTLED
        out.append(f.model_copy(update={"severity": "warn", "summary": f"{prefix} ({why}): {f.summary}", "verdicts": verdicts}))
    return out, n


def count_unsettled(findings: list) -> int:
    get = lambda f: f.summary if hasattr(f, "summary") else f.get("summary", "")  # noqa: E731
    return sum(1 for f in findings if get(f).startswith(UNSETTLED))


def note(n: int, unsettled: int = 0) -> str:
    """The audit's line on judge disagreements and unsettled items (empty when there were none)."""
    out = ""
    if n:
        out += (f"Judge disagreements: {n} (a judge said yes where the audit's judge said no; reported as warnings, not "
                "failures).\n")  # fmt: skip
    if unsettled:
        out += (f"Unsettled: {unsettled} (the reference judge was unsure, below 0.7, either way; reported as warnings: "
                "a failure needs a confident no).\n")  # fmt: skip
    return out
