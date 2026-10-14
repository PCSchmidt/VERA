# ruff: noqa: E501
"""Judge disagreement is not failure (AUD-F-13, Increment 8).

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


def reconcile(
    findings: list[Finding], sentences: list[dict], inferences: list[dict], confirmations: dict[str, object] | None = None
) -> tuple[list[Finding], int]:
    """(findings with judge disagreements turned into warnings, how many were). `sentences` and `inferences` are the
    document's stored records (dumps), whose `verdicts` are the write-time verdicts. `confirmations` maps the trace id of
    an audit "no" to the reference judge's verdict on the same question and material (`cheap_path.CONFIRM_NO`): a
    confident reference yes makes the failure a disagreement; a reference no confirms it and joins its verdicts."""
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
        if ref is not None and _confident(audit_v, False) and _confident(ref, True):
            n += 1
            summary = f"{PREFIX} (failed in the audit, {_describe(audit_v)}; the reference judge says yes, {_describe(ref)}): {f.summary}"
            out.append(f.model_copy(update={"severity": "warn", "summary": summary, "verdicts": [*f.verdicts, ref]}))
            continue
        before = _last(written.get(key, []), audit_v.question_id)
        if before is not None and _confident(audit_v, False) and _confident(before, True) and ref is None:
            n += 1
            summary = f"{PREFIX} (passed at write time, {_describe(before)}; failed in the audit, {_describe(audit_v)}): {f.summary}"
            out.append(f.model_copy(update={"severity": "warn", "summary": summary}))
        elif ref is not None:  # the reference agreed (or was unsure): the failure stands, with its verdict on record
            out.append(f.model_copy(update={"verdicts": [*f.verdicts, ref]}))
        else:
            out.append(f)
    return out, n


def note(n: int) -> str:
    """The audit's line on judge disagreements (empty when there were none)."""
    if not n:
        return ""
    return (
        f"Judge disagreements: {n} (a sentence or statement that passed a judge question when it was written failed the same "
        "question in the audit; reported as warnings, not failures).\n"
    )
