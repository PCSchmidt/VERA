"""Citation check (AUD-F-03) for the loop's own write-up.

The write-up cites only records the loop retrieved (`[R1]`, ...), and its reference list is built by VERA from them.
So, per the SPEC, each reference is matched first against the run's retrieval log (`retrieved.jsonl`); only a
reference the log does not account for is looked up in the bibliographic sources (T5), and one found in neither is a
`fail`. Rules, in order, for each reference-list entry:

1. its key is in the log and its title equals the logged title: verified (evidence from the log);
2. its key is in the log but its text differs from the logged record: `fail` (the list is meant to be built from the
   log, so any difference is an altered reference);
3. its key is not in the log: look the title up (Crossref and arXiv, T5). No candidate: `fail`. Candidates: the judge
   is asked the benchmark's `cite.contains_entry` question over them (near-miss titles are exactly what that
   benchmark was built to measure), so a normalised-title match alone is never trusted for a near-miss. `true`:
   verified (an exact title with a different year is a match with an `info` finding, preprint against journal);
   `false`: `fail`; an unsure verdict or an unavailable lookup: `warn` (unverified, not fabricated).

An in-text citation whose key is neither retrieved nor in the reference list is a `fail`.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.audit.bibliography import LookupUnavailable, normalise
from vera.schemas import Claim, Evidence, Finding, Location, Question, QuestionType, Verdict

# an entry as VERA writes it (vera.loop.references.format_reference): [R1] Authors. Title. 2025. arXiv:... url
ENTRY = re.compile(r"^\[(?P<key>R\d+)\]\s+(?P<authors>.*?)\.\s+(?P<title>.+?)\.\s+(?P<year>\d{4})\.(?P<rest>.*)$")
Ask = Callable[[Question, str], tuple[Verdict, bool]]


def split_references(text: str) -> tuple[str, list[str]]:
    """(body without the reference section, the reference-list lines)."""
    head, sep, tail = text.partition("## References")
    lines = [ln.strip() for ln in tail.splitlines() if ln.strip().startswith("[R")] if sep else []
    return head, lines


def parse_entry(line: str) -> dict:
    m = ENTRY.match(line)
    if not m:
        return {"key": (re.match(r"\[(R\d+)\]", line) or [None, ""])[1], "title": "", "year": "", "raw": line}
    return {"key": m["key"], "authors": m["authors"], "title": m["title"].strip(), "year": m["year"], "raw": line}


def cited_keys(body: str) -> dict[str, str]:
    """Keys cited in the body, each with a short snippet of its first citation."""
    out: dict[str, str] = {}
    for m in re.finditer(r"\[(R\d+)\]", body):
        out.setdefault(m.group(1), body[max(0, m.start() - 60) : m.end() + 20].replace("\n", " "))
    return out


def _claim(key: str, raw: str) -> Claim:
    return Claim(id=f"cite:{key}", kind="citation", text=raw, location=Location(section="References", quote=raw[:200]))


def _candidate_line(i: int, c: dict) -> str:
    authors = ", ".join(c.get("authors", [])[:3])
    return f"[{i}] {authors + '. ' if authors else ''}{c['title']}. {c.get('year', '')}. {c.get('id', '')}".rstrip(". ")


def audit_citations(
    text: str, retrieved: list[dict], ask: Ask, lookup: Callable[[str], list[dict]]
) -> tuple[list[Claim], list[Finding]]:
    body, lines = split_references(text)
    log = {r["key"]: r for r in retrieved}
    claims, findings = [], []
    listed = set()
    for line in lines:
        e = parse_entry(line)
        key = e["key"]
        listed.add(key)
        claim = _claim(key, line)
        claims.append(claim)
        record = log.get(key)
        if record is not None:
            # The list is built from the log, so the logged title must appear in the entry. (Parsing the entry's own
            # title out of the line is unreliable when an author name has an initial: "Scott A. King".)
            if (e["title"] and normalise(e["title"]) == normalise(record["title"])) or (
                normalise(record["title"]) in normalise(line)
            ):
                continue  # verified against the retrieval log
            findings.append(
                Finding(
                    check="citation",
                    severity="fail",
                    claim_ids=[claim.id],
                    verdicts=[],
                    summary=f"Reference {key} differs from the record the loop retrieved: the list says "
                    f"{e['title']!r}, the log has {record['title']!r}.",
                    evidence=[
                        Evidence(
                            claim_id=claim.id,
                            source="log",
                            reference=f"retrieved.jsonl#{key}",
                            matched=False,
                            detail=f"logged title: {record['title']}",
                        )
                    ],
                )
            )
            continue
        findings.append(_lookup_finding(e, claim, ask, lookup))
    for key, snippet in cited_keys(body).items():
        if key not in log and key not in listed:
            cid = f"cite:{key}"
            claims.append(
                Claim(
                    id=cid,
                    kind="citation",
                    text=f"in-text citation [{key}]",
                    location=Location(section="body", quote=snippet),
                )
            )
            findings.append(
                Finding(
                    check="citation",
                    severity="fail",
                    claim_ids=[cid],
                    verdicts=[],
                    summary=f"[{key}] is cited but is not a retrieved record or listed.",
                    evidence=[
                        Evidence(
                            claim_id=cid,
                            source="log",
                            reference="retrieved.jsonl",
                            matched=False,
                            detail=f"no record {key}",
                        )
                    ],
                )
            )
    return claims, [f for f in findings if f is not None]


def _lookup_finding(e: dict, claim: Claim, ask: Ask, lookup: Callable[[str], list[dict]]) -> Finding | None:
    title = e["title"] or e["raw"]
    try:
        candidates = lookup(title)
    except LookupUnavailable as exc:
        return Finding(
            check="citation",
            severity="warn",
            claim_ids=[claim.id],
            verdicts=[],
            summary=f"{e['key']} could not be checked: every bibliographic source failed ({exc}).",
            evidence=[
                Evidence(
                    claim_id=claim.id,
                    source="bibliography_api",
                    reference="crossref, arxiv",
                    matched=None,
                    detail=str(exc),
                )
            ],
        )
    if not candidates:
        return Finding(
            check="citation",
            severity="fail",
            claim_ids=[claim.id],
            verdicts=[],
            summary=f"{e['key']} ({title!r}) is not in the retrieval log and no bibliographic source "
            "returned a matching record.",
            evidence=[
                Evidence(
                    claim_id=claim.id,
                    source="bibliography_api",
                    reference="crossref, arxiv",
                    matched=False,
                    detail="no candidates for the title",
                )
            ],
        )
    candidates = candidates[:8]
    state = "Reference list (candidate records returned by bibliographic sources for the query):\n\n" + "\n".join(
        _candidate_line(i, c) for i, c in enumerate(candidates, 1)
    )
    question = Question(
        id="cite.contains_entry",
        type=QuestionType.BOOLEAN,
        text=f'Does the reference list above contain an entry for the paper titled "{title}"? '
        "Answer true only if one of the listed entries is that paper.",
    )
    verdict, confident = ask(question, state)
    best = max(candidates, key=lambda c: _similar(title, c["title"]))
    ref = best.get("url") or best.get("id") or best["source"]
    if not confident:
        return Finding(
            check="citation",
            severity="warn",
            claim_ids=[claim.id],
            verdicts=[verdict],
            summary=f"{e['key']} ({title!r}) could not be confirmed: the judge was not confident.",
            evidence=[
                Evidence(
                    claim_id=claim.id,
                    source="bibliography_api",
                    reference=ref,
                    matched=None,
                    detail="closest candidate: " + best["title"],
                )
            ],
        )
    if verdict.answer is True:
        year_note = bool(e["year"] and best.get("year") and e["year"] != best["year"])
        if year_note and normalise(best["title"]) == normalise(title):
            return Finding(
                check="citation",
                severity="info",
                claim_ids=[claim.id],
                verdicts=[verdict],
                summary=f"{e['key']} matches a published record, with a different year "
                f"({e['year']} cited, {best['year']} in {best['source']}).",
                evidence=[
                    Evidence(
                        claim_id=claim.id,
                        source="bibliography_api",
                        reference=ref,
                        matched=True,
                        detail=f"year differs: {best['year']}",
                    )
                ],
            )
        return None  # verified through a bibliographic source: no finding needed
    return Finding(
        check="citation",
        severity="fail",
        claim_ids=[claim.id],
        verdicts=[verdict],
        summary=f"{e['key']} ({title!r}) is not in the retrieval log, and the records returned for it "
        "are different papers.",
        evidence=[
            Evidence(
                claim_id=claim.id,
                source="bibliography_api",
                reference=ref,
                matched=False,
                detail="closest candidate: " + best["title"],
            )
        ],
    )


def _similar(a: str, b: str) -> float:
    import difflib  # noqa: PLC0415

    return difflib.SequenceMatcher(None, normalise(a), normalise(b)).ratio()
