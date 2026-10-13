# ruff: noqa: E501
"""Sentence status (RSH-F-15, Increment 7): every sentence of a review or a paper's evidence sections is a claim, a
synthesis or a transition, and each kind has its check.

Increment 6's papers audited green while uncited sentences were wrong ("The two studies therefore disagree", both cited
sentences one source), a claim-free sentence named a source ("Shao and colleagues"), quotes leaned on context outside
them ("However, this patch may be overfitting.") and claims said more than their quotes. This module holds what the
verify step (`synthesis_stage.verify_sentences`) and the audit (`vera.audit.sentences`) need for that:

- `SENTENCE_RULE`, appended to the drafting prompts: each sentence has a `ref`, claim-free sentences declare a `kind`,
  and a synthesis lists the refs of the claim sentences it rests on as `premises`; `parse_typed` reads them;
- deterministic rules, no model call: `agreement_problem` (agreement or disagreement needs premises from two sources),
  `absence_problem` (what the evidence lacks is stated in the record, not in an evidence section), `names_a_source`
  ("X and colleagues", "X's team", besides the earlier rules), `leans_on_context` and `widen_quote` (a quote that opens
  with a back-reference is extended with the sentence before it in the same passage), `mark_same_quotes` (a claim
  reusing an earlier claim's quote is marked, and quotes are counted once);
- two judge questions: `within_quote` (`claim.within_quote`: does the claim say only what its quote says?) and `no_fact`
  (`sentence.no_fact`: does a transition state no fact?).

The frozen files (`synthesis.py`, `reading.py`, `questions.py`, `vera/audit/*` listed in audit_hash_incr5.json) and the
files hashed for Increment 6's inference measurement (`anchoring.py`, `vera/audit/inference.py`) are imported, not edited.
"""

from __future__ import annotations

import re

from vera.audit import inference
from vera.literature import anchoring, reading, synthesis
from vera.schemas import ClaimLink, Question, QuestionType, SentenceRecord

KINDS = ("claim", "synthesis", "transition")

SENTENCE_RULE = (
    '\n\nGive every sentence a "ref" ("s1", "s2", ... in order across your reply). A sentence with "claim": null must also '
    'have a "kind": "transition" if it only introduces, orders or signposts and states no fact about the literature, or '
    '"synthesis" if it compares, contrasts, generalises or counts across claims. A synthesis must list in "premises" the '
    'refs of the earlier claim sentences of your reply that it rests on, for example "premises": ["s2", "s5"], and say '
    "nothing those claims do not support. A synthesis may say that studies agree, disagree or converge only if its "
    "premises come from at least two different sources. Do not write what the evidence does not contain or what is not "
    'established ("no passage covers ...", "no study examines ..."): the method and threats sections report that '
    "from the run's records."
)

# ── reading the writer's typed sentences ───────────────────────────────────────────────────────────────


def parse_typed(data: object) -> list[list[dict]]:
    """`synthesis.parse_sentences` (frozen: it keeps `text` and `claim` only), with each sentence's `kind`, `ref` and
    `premises` added from the same JSON. A sentence with a claim is a claim sentence whatever it declares; a claim-free
    sentence that declares nothing is a transition (and is checked for stating no fact)."""
    paragraphs = synthesis.parse_sentences(data)
    raw = []
    if isinstance(data, dict) and isinstance(data.get("paragraphs"), list):
        for para in data["paragraphs"]:
            row = [s for s in (para if isinstance(para, list) else [])
                   if isinstance(s, dict) and (s.get("text") or "").strip()]  # fmt: skip
            if row:
                raw.append(row)
    n = 0
    for para, rpara in zip(paragraphs, raw, strict=False):
        for s, r in zip(para, rpara, strict=False):
            n += 1
            typed(s, r, n)
    for para in paragraphs[len(raw) :]:  # cannot happen with parse_sentences as written; kept total for safety
        for s in para:
            n += 1
            typed(s, {}, n)
    return paragraphs


def typed(s: dict, raw: dict, n: int) -> dict:
    """Fill `kind`, `ref` and `premises` on a parsed sentence from its raw JSON (in place; returned for convenience)."""
    kind = raw.get("kind") if raw.get("kind") in ("synthesis", "transition") else "transition"
    premises = raw.get("premises") if isinstance(raw.get("premises"), list) else []
    s["kind"] = "claim" if s.get("claim") else kind
    s["ref"] = str(raw.get("ref") or f"s{n}")
    s["premises"] = [str(p) for p in premises] if s["kind"] == "synthesis" else []
    return s


def ensure_typed(paragraphs: list[list[dict]]) -> list[list[dict]]:
    """Drafts made before sentence status (a resumed run) carry no kind: claim sentences are claims, the rest
    transitions. Refs are added where missing, unique across the draft."""
    n, seen = 0, set()
    for para in paragraphs:
        for s in para:
            n += 1
            if "kind" not in s:
                typed(s, {}, n)
            if s["ref"] in seen:
                s["ref"] = f"{s['ref']}-{n}"
            seen.add(s["ref"])
    return paragraphs


# ── deterministic rules ──────────────────────────────────────────────────────────────────────────────

_COLLEAGUES = re.compile(
    r"\b[A-Z][\w-]+(?:\s+et\s+al\.?)?\s+and\s+(?:colleagues|co-?authors|co-?workers|collaborators|team)\b"
    r"|\b[A-Z][\w-]+['’]s\s+(?:team|group|lab|colleagues|study|paper|work)\b"
    r"|\bthe\s+[A-Z][\w-]+\s+(?:group|team|lab)\b"
)


def names_a_source(text: str) -> str | None:
    """A source named in a sentence with no claim behind it, or None: the review's earlier rules (`[Rn]`, a bare `R12`,
    "et al", an author-year) and "X and colleagues", "X's team", "the X group"."""
    m = synthesis.STRAY_ATTRIBUTION.search(text)
    if m:
        return m.group(0)
    return anchoring.names_a_source_without_a_claim(text) or (
        _COLLEAGUES.search(text).group(0) if _COLLEAGUES.search(text) else None
    )


_ABSENCE = re.compile(
    r"\b(?:no|none of the|not a single|not one)\s+(?:\w+\s+){0,2}?(?:passages?|stud(?:y|ies)|papers?|sources?|works?|"
    r"evidence|results?|experiments?|evaluations?)\b(?!\s+(?:of|than)\b)"
    r"|\b(?:evidence|passages|sources|studies|literature|papers)\s+(?:here\s+|reviewed\s+|available\s+)?(?:do|does)\s+not\s+"
    r"(?:cover|address|examine|report|include|show|establish|measure|evaluate|test)\b"
    r"|\bnot\s+(?:yet\s+)?(?:been\s+)?established\b|\bunestablished\b|\bremains?\s+(?:unexamined|unstudied|unmeasured|untested)\b",
    re.I,
)


def absence_problem(text: str) -> str | None:
    """A statement about what the evidence lacks, or None. In an evidence section it is removed: what retrieval did not
    find is stated in the record (method, threats, the review's retrieval note) from the run's files, where it cannot
    contradict a claim the paper does make."""
    m = _ABSENCE.search(text)
    return f"absence: {m.group(0)!r} belongs in the record sections, not the evidence" if m else None


_AGREEMENT = re.compile(
    r"\b(?:agree[sd]?|agreement|disagree\w*|converg\w*|diverg\w*|conflict\w*|contradict\w*|corroborat\w*|"
    r"consistent(?:ly)?\s+(?:with each other|across)|in line with each other|"
    r"(?:both|the two|several|multiple|many|various|independent)\s+(?:\w+\s+)?(?:studies|papers|sources|groups|works|evaluations)|"
    r"across\s+(?:the\s+)?(?:studies|papers|sources))\b",
    re.I,
)


def agreement_problem(text: str, premises: list[str], source_of: dict[str, str]) -> str | None:
    """A statement that says studies agree, disagree or converge (or that "the two" or "several" studies show something)
    whose premises come from fewer than two distinct sources, or None. `source_of` maps premise -> source key."""
    m = _AGREEMENT.search(text)
    if not m:
        return None
    sources = {source_of[p] for p in premises if p in source_of}
    if len(sources) >= 2:
        return None
    return f"speaks of several sources ({m.group(0)!r}) but its premises come from {len(sources)} source"


_LEANS = re.compile(
    r"^\W*(?:(?:however|moreover|thus|therefore|hence|also|furthermore|in addition|instead|still|yet|but|and|so|"
    r"in particular|in this case|as a result|for example)\s*,?\s+)?"
    r"(?:this|these|that|those|such|it|they|its|their|the latter|the former|he|she)\b",
    re.I,
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def leans_on_context(quote: str) -> bool:
    """The quote opens with a back-reference ("This", "However, this patch", "These results"), so what it is about is
    outside it."""
    return bool(_LEANS.match(quote))


def widen_quote(quote: str, passage_text: str) -> str | None:
    """The quote extended back to include the whole sentence before the one it starts in, verbatim from the passage, or
    None when the passage has no earlier sentence (or the quote cannot be located in it)."""
    sents = [s for s in _SENTENCE_END.split(passage_text.strip()) if s.strip()]
    start = next((i for i in range(len(sents))
                  if reading.quote_in_text(quote, " ".join(sents[i:]))
                  and not reading.quote_in_text(quote, " ".join(sents[i + 1:]))), None)  # fmt: skip
    if not start:  # None, or the quote starts in the passage's first sentence
        return None
    end = next(
        (k for k in range(start, len(sents)) if reading.quote_in_text(quote, " ".join(sents[start : k + 1]))), None
    )
    if end is None:
        return None
    wider = " ".join(sents[start - 1 : end + 1])
    return wider if reading.quote_in_text(wider, passage_text) else None


def mark_same_quotes(claims: list[ClaimLink]) -> list[ClaimLink]:
    """Each claim whose (source, quote) an earlier claim already used gets `same_quote_as` = that claim's id: it is a
    second sentence on one piece of evidence, not a second finding."""
    first: dict[tuple[str, str], str] = {}
    out = []
    for c in claims:
        key = (c.source_key, reading.norm_for_quote(c.quote).strip(" .\"'"))
        earlier = first.setdefault(key, c.id or "")
        out.append(c.model_copy(update={"same_quote_as": earlier}) if earlier != (c.id or "") else c)
    return out


def distinct_quotes(claims: list) -> int:
    def key(c: object) -> tuple[str, str]:
        src, quote = (c["source_key"], c["quote"]) if isinstance(c, dict) else (c.source_key, c.quote)
        return src, reading.norm_for_quote(quote).strip(" .\"'")

    return len({key(c) for c in claims})


# ── judge questions ──────────────────────────────────────────────────────────────────────────────────


def within_quote(claim: str, quote: str, title: str | None = None) -> tuple[Question, str]:
    """(question, material): does the claim say only what its quote says? Shown the claim and the quote only."""
    source = f'Source: "{title}"\n' if title else ""
    material = f"{source}Claim: {claim}\n\nQuote from that source: {quote}"
    text = (
        "Does the claim say only what the quote says? Answer false if the claim adds anything the quote does not state: "
        "a name, a number, a model or dataset, a characterisation or label the quote does not use, a wider scope, or a "
        "cause or consequence. Rewording that keeps the quote's meaning, and naming the source, count as the quote's."
    )
    return Question(id="claim.within_quote", type=QuestionType.BOOLEAN, text=text), material


def no_fact(text: str, heading: str = "") -> tuple[Question, str]:
    """(question, material): does a claim-free sentence state no fact (only introduce, order or signpost)?"""
    where = f'Section: "{heading}"\n' if heading else ""
    material = f"{where}Sentence: {text}"
    q = (
        "This sentence of a literature review cites no source. Does it state no fact about the literature, a study, a "
        "method, a result or the evidence, only introducing, ordering or signposting what follows? Answer false if it "
        "states a finding, a comparison, a count, a generalisation, a cause, or what the evidence does or does not show."
    )
    return Question(id="sentence.no_fact", type=QuestionType.BOOLEAN, text=q), material


def follows_strict(text: str, premises: list[str], claims: dict[str, str]) -> tuple[Question, str]:
    """(question, material): the inference question, worded clause by clause (Increment 7, tuned on the dev split only).

    Increment 6's wording (`vera.audit.inference.follows`, kept unchanged so its measurement stays reproducible) passed
    all five overreaching statements the external review named in P1: "rarely captured" from "may lack motivation", a
    reading of one feature generalised to all, a premise that says the opposite, and an absence in the set read as an
    absence in general. The question id is the same; the wording is not."""
    listed = "\n".join(f"{p}: {claims[p]}" for p in premises)
    material = f"Claims (each verified against a quote from its source):\n{listed}\n\nStatement: {inference.PREMISE_MARKER.sub('', text).strip()}"
    q = (
        "Check the statement clause by clause against these claims alone. Answer false if any clause: adds a fact, "
        "number, cause or generalisation the claims do not state; states more strongly than the claims do (turns "
        "'may', 'some', 'one study' or 'reported' into 'is', 'rarely', 'always', 'the central' or 'the claims agree'); "
        "treats what these claims do not mention as absent or unknown in general; rests on a claim that says the "
        "opposite or does not bear on it; or counts one source's findings as several sources agreeing. A cautious "
        "combination of the claims, or a question they leave open, counts as following."
    )
    return Question(id="paper.inference_follows", type=QuestionType.BOOLEAN, text=q), material


def check_statement(text: str, premises: list[str], claims: dict[str, str], ask, source_of: dict[str, str] | None = None):
    """A synthesis sentence or an interpretation statement, as the new checks run it: the Increment 6 rules
    (`inference.statement_problem`), "X and colleagues", the agreement rule (when `source_of` is given), then the
    clause-by-clause judge question. Returns (reason or None, verdicts); an unsure judge is a failure."""
    problem = inference.statement_problem(text, premises, claims)
    if problem:
        return problem, []
    body = inference.PREMISE_MARKER.sub("", text)
    named = names_a_source(body)
    if named:
        return f"cites a source directly: {named!r}", []
    if source_of is not None:
        agree = agreement_problem(body, premises, source_of)
        if agree:
            return agree, []
    q, material = follows_strict(text, premises, claims)
    v, confident = ask(q, material)
    if not confident:
        return "judge_unsure", [v]
    return (None if v.answer is True else "does not follow from its premises"), [v]


# ── repair of claim-free sentences ───────────────────────────────────────────────────────────────────


def repair_prompt(question: str, failed: list[dict], kept_claims: list[dict]) -> str:
    """One call for a section's failed synthesis and transition sentences, shown the claim sentences that survived."""
    claims = "\n".join(f"{c['ref']} ({c['claim']['source_key']}): {c['text']}" for c in kept_claims) or "(none)"
    items = "\n".join(f"{i + 1}. [{f['why']}] {f['text']}" for i, f in enumerate(failed))
    return (
        f"Research question: {question}\n\nThese sentences of a literature review cite no source and failed their checks. "
        "For each, rewrite it either as a transition that states no fact about the literature, or as a synthesis that "
        "says only what the claim sentences below support and names them as premises (two or more sources if it says "
        "they agree or differ). Do not name a source, author or system, and do not say what the evidence lacks. Use "
        "null to drop a sentence.\n\n"
        f"{items}\n\nClaim sentences (ref, source, text):\n{claims}\n\n"
        'Reply with JSON: a list in the same order, each {"text": "...", "kind": "transition" or "synthesis", '
        '"premises": ["s2", ...]} or null.'
    )


# ── the record of every sentence ─────────────────────────────────────────────────────────────────────


def sentence_records(log: list[dict], claim_ids: list[str], section: str, start: int = 0) -> list[SentenceRecord]:
    """`SentenceRecord`s from `verify_sentences`'s log. `claim_ids` are the ids of the section's kept claims in reading
    order (the order `synthesis.assemble` emits them), so the n-th kept claim sentence carries the n-th id and a
    synthesis's premise refs become those ids. Ids run on from `start` across a document's sections."""
    ids = iter(claim_ids)
    of_ref = {e["ref"]: next(ids) for e in log if e["kind"] == "claim" and e["status"] == "pass"}
    out = []
    for n, e in enumerate(log, start=start + 1):
        kept = e["status"] == "pass"
        claims = [of_ref[e["ref"]]] if e["kind"] == "claim" and e["ref"] in of_ref else []
        premises = [of_ref[p] for p in e["premises"] if p in of_ref] if e["kind"] == "synthesis" else []
        out.append(SentenceRecord(id=f"S{n}", section=section, text=e["text"], kind=e["kind"], claims=claims,
                                  premises=premises, verdicts=e["verdicts"], status="pass" if kept else "removed",
                                  reason=e["reason"]))  # fmt: skip
    return out
