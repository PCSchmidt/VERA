# ruff: noqa: E501
"""The sentence audit (AUD-F-12, Increment 7): every sentence of a review or a paper's evidence sections, re-checked.

The frozen literature audit checks each cited claim against its passage. This module checks what it does not:

- **claim sentences**: does the claim say more than its quote (`claim.within_quote`)? Does the quote lean on context
  outside it (a back-reference the verify step should have widened)?
- **claim-free sentences**: one that names a source or says what the evidence lacks fails by rule; a synthesis must name
  existing claims, speak of several sources only with premises from two, and be judged to follow from them
  (`vera.audit.inference.check`); a transition must be judged to state no fact (`sentence.no_fact`).

Documents made before sentence statuses existed (Increment 6's papers, earlier reviews) have no sentence records: their
evidence text is split into sentences, a sentence with a citation marker is a claim sentence (claims in reading order),
and a claim-free sentence that the judge finds states a fact is checked as a synthesis of its section's claims. One that
follows is reported as a warning (it names no premises), one that does not as a failure.

A confident failure is `fail`; an unsure verdict is `warn`. This module is new and not one of the frozen audit files.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.literature import sentence_checks
from vera.schemas import Evidence, Finding, Question, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_CITE = re.compile(r"\[R\d+\]")


def split(text: str) -> list[str]:
    """Sentences of a section's text, paragraph by paragraph (the same split the real-case set uses)."""
    return [s for para in text.split("\n\n") for s in _SENT.split(para.strip()) if s.strip()]


def from_text(sections: list[tuple[str, str]], claim_ids: list[str]) -> list[dict]:
    """Sentence entries for a document without sentence records: (heading, text) per evidence section, and the claim ids
    in reading order (each citation marker is one claim). Claim-free sentences get kind "unrecorded"."""
    ids, out = iter(claim_ids), []
    for heading, text in sections:
        section_claims: list[str] = []
        entries = []
        for s in split(text):
            if _CITE.search(s):
                cid = next(ids, None)
                if cid:
                    section_claims.append(cid)
                entries.append({"id": f"S{len(out) + len(entries) + 1}", "section": heading, "text": s, "kind": "claim",
                                "claims": [cid] if cid else [], "premises": []})  # fmt: skip
            else:
                entries.append({"id": f"S{len(out) + len(entries) + 1}", "section": heading, "text": s,
                                "kind": "unrecorded", "claims": [], "premises": []})  # fmt: skip
        for e in entries:
            e["section_claims"] = section_claims
        out += entries
    return out


def from_records(records: list[dict]) -> list[dict]:
    """Sentence entries from a document's `SentenceRecord` dumps: the kept ones are in the text."""
    return [dict(r, section_claims=[]) for r in records if r.get("status") == "pass"]


def _finding(entry: dict, severity: str, reason: str, verdicts: list[Verdict], reference: str) -> Finding:
    summary = f"{entry['id']} ({entry['section'] or 'review'}, {entry['kind']}): {reason}: {entry['text'][:140]!r}"
    return Finding(check="sentence", severity=severity, claim_ids=list(entry["claims"]) or [entry["id"]], verdicts=verdicts,
                   summary=summary, evidence=[Evidence(claim_id=entry["id"], source="log", reference=reference,
                                                       matched=False, detail=summary)])  # fmt: skip


def check_entry(entry: dict, claims: dict[str, dict], ask: Ask) -> tuple[str | None, str | None, list[Verdict]]:
    """(severity, reason, verdicts) for one sentence; severity None when it passes. `claims` maps claim id ->
    {"claim", "quote", "source_key", "title"}."""
    kind, text = entry["kind"], entry["text"]
    if kind == "claim":
        verdicts = []
        for cid in entry["claims"]:
            c = claims.get(cid)
            if c is None:
                return "fail", f"names claim {cid}, which the document does not have", verdicts
            if sentence_checks.leans_on_context(c["quote"]):
                return "warn", f"the quote of {cid} opens with a back-reference, so what it is about is outside it", verdicts
            q, material = sentence_checks.within_quote(c["claim"], c["quote"], c.get("title"))
            v, confident = ask(q, material)
            verdicts.append(v)
            if not confident:
                return "warn", f"judge unsure whether {cid} says more than its quote", verdicts
            if v.answer is not True:
                return "fail", f"{cid} says more than its quote", verdicts
        return None, None, verdicts
    named = sentence_checks.names_a_source(text)
    if named:
        return "fail", f"names a source without a claim: {named!r}", []
    absence = sentence_checks.absence_problem(text)
    if absence:
        return "fail", absence, []
    claim_text = {cid: f"{c['claim']} (source: {c.get('title') or c['source_key']})" for cid, c in claims.items()}
    source_of = {cid: c["source_key"] for cid, c in claims.items()}
    if kind == "synthesis":
        why, verdicts = sentence_checks.check_statement(text, entry["premises"], claim_text, ask, source_of)
        if why is None:
            return None, None, verdicts
        return ("warn" if why == "judge_unsure" else "fail"), f"synthesis: {why}", verdicts
    q, material = sentence_checks.no_fact(text, entry["section"])
    v, confident = ask(q, material)
    if confident and v.answer is True:
        return None, None, [v]
    if kind == "transition":  # recorded as stating no fact, but the judge says it does (or is unsure)
        return ("fail" if confident else "warn"), "a transition that states a fact" if confident else "judge unsure whether a transition states a fact", [v]
    # unrecorded (a document made before sentence statuses): check it as a synthesis of its section's claims
    premises = [p for p in entry["section_claims"] if p in claims]
    if not premises:
        return "fail", "states a fact, and its section has no claim it could rest on", [v]
    why, verdicts = sentence_checks.check_statement(text, premises, claim_text, ask, source_of)
    if why is None:
        return "warn", "states a fact without naming its premises; judged to follow from its section's claims", [v, *verdicts]
    severity = "warn" if why == "judge_unsure" else "fail"
    return severity, f"states a fact that does not follow from its section's claims ({why})", [v, *verdicts]


def audit(entries: list[dict], claims: dict[str, dict], ask: Ask, reference: str) -> tuple[list[Finding], dict[str, int]]:
    """Findings for every sentence, and counts by kind and outcome."""
    findings, counts = [], {"sentences": len(entries)}
    for e in entries:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        severity, reason, verdicts = check_entry(e, claims, ask)
        if severity:
            counts[severity] = counts.get(severity, 0) + 1
            findings.append(_finding(e, severity, reason, verdicts, reference))
    return findings, counts


def audit_inferences(inferences: list[dict], claims: dict[str, str], source_of: dict[str, str], ask: Ask) -> list[Finding]:
    """`vera.audit.inference.audit`, with the new checks (`sentence_checks.check_statement`): the paper's kept
    interpretation statements re-checked; a failure is `fail`, an unsure verdict `warn`."""
    findings = []
    for inf in (i for i in inferences if i.get("status") == "pass"):
        reason, verdicts = sentence_checks.check_statement(inf["text"], inf["premises"], claims, ask, source_of)
        if reason is None:
            continue
        summary = f"{inf['id']} ({inf['section']}): {reason}: {inf['text'][:140]!r}"
        findings.append(Finding(check="inference", severity="warn" if reason == "judge_unsure" else "fail",
                                claim_ids=[inf["id"]], verdicts=verdicts, summary=summary,
                                evidence=[Evidence(claim_id=inf["id"], source="log", reference="paper/inferences.jsonl",
                                                   matched=False, detail=summary)]))  # fmt: skip
    return findings


def note(counts: dict[str, int]) -> str:
    """The audit's paragraph on its sentences, from the counts."""
    kinds = ", ".join(f"{counts[k]} {k}" for k in ("claim", "synthesis", "transition", "unrecorded") if counts.get(k))
    return (
        f"\nSentences re-checked: {counts.get('sentences', 0)} ({kinds}); {counts.get('fail', 0)} failed and "
        f"{counts.get('warn', 0)} were flagged. Claims were checked to say no more than their quotes; sentences without "
        "a claim were checked to state no fact, or to follow from the claims they rest on.\n"
    )
