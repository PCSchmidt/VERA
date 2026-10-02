"""Audit of a literature section (AUD-F-03 on the loop's own text, AUD-F-10): every attribution is linked and checked.

The section is the text a reader sees (`literature.md`); the evidence it must stand on is the run's own record:
`claims.jsonl` (what each cited sentence claims, and the quote it rests on), `passages.jsonl` (the only text the
synthesis may quote) and `retrieved.jsonl` (the sources). The audit does not trust that the section was built from
them: it checks, for the text as written,

1. **every `[Rn]` is a retrieved record** and the reference list says what the log says (`citation`, fail);
2. **every cited sentence has a claim behind it** (a sentence with `[Rn]` and no claim is an attribution nobody
   checked) and **cites the source its claim is linked to** (a changed key, or a sentence moved to a different
   source, is a `citation` fail);
3. **the claim's quote is a verbatim span of a passage of that source** (`claim_support`, fail: a fabricated quote, or a
   real quote under the wrong source);
4. **the judge path says the passage supports the claim** as written (`claim_support`: a confident "no" is a fail, an
   unsure verdict a warn), through the same `lit.claim_supported` question the claim-support benchmark measures.

Each finding carries evidence that points at the log line, the claim or the passage.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.audit.bibliography import normalise
from vera.audit.citations import audit_citations
from vera.literature import questions, synthesis
from vera.schemas import Claim, Evidence, Finding, Location, Question, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
MARKER = re.compile(r"\s*\[(R\d+)\]")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[\(\"*])")


def cited_sentences(text: str) -> list[tuple[str, str, list[str]]]:
    """(section, stem, keys) for each sentence of the body that carries `[Rn]` markers; the stem is the sentence
    without its markers."""
    body = text.partition("## References")[0]
    out, section = [], ""
    for block in body.split("\n"):
        line = block.strip()
        if not line:
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        for sentence in SENTENCE.split(line):
            keys = MARKER.findall(sentence)
            if keys:
                out.append((section, MARKER.sub("", sentence).strip(), keys))
    return out


def _finding(check: str, severity: str, claim: Claim, reference: str, matched: bool | None, summary: str,
             verdicts=()) -> Finding:  # fmt: skip
    return Finding(check=check, severity=severity, claim_ids=[claim.id], verdicts=list(verdicts), summary=summary,
                   evidence=[Evidence(claim_id=claim.id, source="log", reference=reference, matched=matched,
                                      detail=summary)])  # fmt: skip


def link(stem: str, normalised: list[tuple[str, dict]]) -> dict | None:
    """The claim a cited sentence stands for. A claim may span two sentences of the text, so the stem is matched inside
    the claim (or the claim inside the stem); a stem too short to identify anything links to nothing."""
    n = normalise(stem)
    if len(n) < 30:
        return None
    return next((c for n_claim, c in normalised if n in n_claim or n_claim in n), None)


def audit_literature(
    text: str, claims: list[dict], passages: list[dict], retrieved: list[dict], ask: Ask
) -> tuple[list[Claim], list[Finding]]:
    log = {r["key"]: r for r in retrieved}
    audit_claims, findings = audit_citations(text, retrieved, ask, lambda title: [])  # the log is the only source
    normalised = [(normalise(c["claim"]), c) for c in claims]
    for n, (section, stem, keys) in enumerate(cited_sentences(text)):
        claim = Claim(id=f"lit:{n}", kind="citation", text=stem,
                      location=Location(section=section or None, quote=stem[:200]))  # fmt: skip
        audit_claims.append(claim)
        linked = link(stem, normalised)
        if linked is None:
            cited = ", ".join(f"[{k}]" for k in keys)
            findings.append(_finding("citation", "fail", claim, "claims.jsonl", False,
                                     f"{cited} cited with no claim behind it (an attribution the synthesis never "
                                     f"checked): {stem[:140]!r}"))  # fmt: skip
            continue
        if linked["source_key"] not in keys or len(keys) != 1:
            cited = ", ".join(f"[{k}]" for k in keys)
            findings.append(_finding("citation", "fail", claim, "claims.jsonl", False,
                                     f"The sentence cites {cited} but its claim is linked to [{linked['source_key']}]: "
                                     f"{stem[:140]!r}"))  # fmt: skip
            continue
        key = linked["source_key"]
        if key not in log:
            continue  # already a citation fail above
        mine = [p for p in passages if p["source_key"] == key]
        status, why = synthesis.check_claim(linked, log, passages)
        if status == "fail":
            where = "another source's passage" if why == "wrong_source" else "any passage"
            findings.append(_finding("claim_support", "fail", claim, f"passages.jsonl#{key}", False,
                                     f"The quote behind this claim is not in [{key}]: it appears in {where} or nowhere "
                                     f"({why}): {linked['quote'][:100]!r}"))  # fmt: skip
            continue
        passage = synthesis.matched_passage(linked, mine) or mine[0]
        question, material = questions.claim_supported(stem, passage, log[key]["title"])
        verdict, confident = ask(question, material)
        ref = f"passages.jsonl#{passage['id']}"
        if not confident:
            findings.append(_finding("claim_support", "warn", claim, ref, None,
                                     f"Could not confirm the claim against its passage (the judge was not confident): "
                                     f"{stem[:140]!r}", [verdict]))  # fmt: skip
        elif verdict.answer is not True:
            findings.append(_finding("claim_support", "fail", claim, ref, False,
                                     f"The passage cited does not support the claim as written: {stem[:140]!r}",
                                     [verdict]))  # fmt: skip
    return audit_claims, findings
