"""Synthesis with verified claims (RSH-F-09, AUD-F-10): a literature section in which every attribution carries a quote.

The generator writes the section as sentences. A sentence that attributes something to a source carries a **claim**: the
source key, the passage id and a quote copied from that passage. It does not write the `[Rn]` markers itself: VERA adds
them from the claim's source key, so a citation exists only where a claim does, and the reference list is built from
the retrieval log, never from model text.

Every claim is checked, in this order, and every outcome is kept as evidence:

1. the source key is a retrieved record (`unresolved_source`);
2. the quote is a verbatim (normalised) span of a passage of that source (`fabricated_quote`: nowhere in the evidence;
   `wrong_source`: it is in another source's passage, so the key and the quote do not belong together);
3. the cheap judge path, a component other than the producer, says the passage supports the claim as written
   (`lit.claim_supported`).

A claim that fails is sent back once for repair; if it still fails the sentence is removed (and counted). The section
keeps only claims that passed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from vera.literature import reading
from vera.loop.references import format_reference

# A sentence with no claim that still names a source: an attribution nobody checked, removed by the verify step.
STRAY_ATTRIBUTION = re.compile(r"\[R\d+\]|\bet al\b|\(\s*[A-Z][a-z]+,? (?:and [A-Z][a-z]+,? )?\d{4}\s*\)")

SYSTEM = (
    "You are a careful research writer. You write literature reviews that say only what the supplied passages support. "
    "Reply only with what is asked, in the requested format."
)


def passages_block(passages: list[dict], records: dict[str, dict]) -> str:
    """The evidence as the generator sees it: each passage under its source, with its id and locator."""
    lines = []
    for key in dict.fromkeys(p["source_key"] for p in passages):
        rec = records[key]
        lines.append(f"\n[{key}] {rec['title']} ({rec.get('year') or 'n.d.'})")
        for p in (p for p in passages if p["source_key"] == key):
            lines.append(f"  <{p['id']}> ({p['locator']}) {p['text']}")
    return "\n".join(lines)


def draft_prompt(question: str, passages: list[dict], records: dict[str, dict], max_words: int | None) -> str:
    return (
        f"Research question: {question}\n\n"
        "Write a short literature review section that answers the question from the evidence below: what the sources "
        "establish, where they agree or differ, and where they stop (say plainly what is NOT established). Use only "
        "the passages below.\n\n"
        "Write it as paragraphs of sentences. For every sentence that attributes a finding, method or statement to a "
        'source, give a "claim": {"source_key": "R3", "passage_id": "R3-P2", "quote": "..."} where the quote is copied '
        "word for word from that passage (at least 25 characters, no ellipsis). Do not write citation markers "
        "yourself; they are added from the claims. A sentence that attributes nothing (a transition, or a statement "
        'of what is not established) has "claim": null. One claim per sentence, and one source per claim.'
        + (f"\n\nAt most {max_words} words in all." if max_words else "")
        + '\n\nReply with JSON: {"paragraphs": [[{"text": "...", "claim": {...} or null}, ...], ...]}.\n\n'
        f"Evidence:\n{passages_block(passages, records)}"
    )


def repair_prompt(question: str, failures: list[dict], passages: list[dict], records: dict[str, dict]) -> str:
    items = "\n".join(f"{i + 1}. [{f['why']}] {f['text']}  (cited {f['claim']['source_key']}, "
                      f"quote: {f['claim']['quote']!r})" for i, f in enumerate(failures))  # fmt: skip
    return (
        f"Research question: {question}\n\nThese sentences of a literature review failed their checks. For each, "
        "either rewrite it so that the quote really is a word-for-word span of a passage below and the sentence says "
        'only what that passage supports, or drop it by giving "text": null.\n\n'
        f"{items}\n\n"
        'Reply with JSON: a list in the same order, each {"text": "..." or null, "claim": {"source_key": "R3", '
        '"passage_id": "R3-P2", "quote": "..."} or null}.\n\n'
        f"Evidence:\n{passages_block(passages, records)}"
    )


def parse_sentences(data: object) -> list[list[dict]]:
    """Paragraphs of sentences `{"text", "claim"}` from the model's JSON; malformed entries are skipped."""
    out: list[list[dict]] = []
    if not isinstance(data, dict):
        return out
    for para in data.get("paragraphs", []) if isinstance(data.get("paragraphs"), list) else []:
        sentences = []
        for s in para if isinstance(para, list) else []:
            text = (s.get("text") or "").strip() if isinstance(s, dict) else ""
            if not text:
                continue
            claim = s.get("claim")
            if isinstance(claim, dict) and claim.get("source_key") and claim.get("quote"):
                claim = {"source_key": str(claim["source_key"]), "passage_id": str(claim.get("passage_id") or ""),
                         "quote": str(claim["quote"])}  # fmt: skip
            else:
                claim = None
            sentences.append({"text": text, "claim": claim})
        if sentences:
            out.append(sentences)
    return out


def check_claim(claim: dict, records: dict[str, dict], passages: list[dict]) -> tuple[str, str | None]:
    """The deterministic checks: ("pass", None) or ("fail", reason code). Returns the passage text it matched on."""
    if claim["source_key"] not in records:
        return "fail", "unresolved_source"
    mine = [p for p in passages if p["source_key"] == claim["source_key"]]
    if any(reading.quote_in_text(claim["quote"], p["text"]) for p in mine):
        return "pass", None
    if any(reading.quote_in_text(claim["quote"], p["text"]) for p in passages):
        return "fail", "wrong_source"
    return "fail", "fabricated_quote"


def matched_passage(claim: dict, passages: list[dict]) -> dict | None:
    """The passage of the claimed source that holds the quote (the one the judge is shown)."""
    return next((p for p in passages if p["source_key"] == claim["source_key"]
                 and reading.quote_in_text(claim["quote"], p["text"])), None)  # fmt: skip


@dataclass
class Checked:
    sentences: list[list[dict]]
    stats: dict = field(default_factory=dict)


def assemble(paragraphs: list[list[dict]]) -> tuple[str, list[dict]]:
    """The section text, with `[Rn]` after each sentence that carries a (passed) claim, and the claims in order."""
    claims, blocks = [], []
    for para in paragraphs:
        parts = []
        for s in para:
            if s["claim"]:
                claims.append({"claim": s["text"], **s["claim"]})
                parts.append(f"{s['text'].rstrip('.')} [{s['claim']['source_key']}].")
            else:
                parts.append(s["text"])
        if parts:
            blocks.append(" ".join(parts))
    return "\n\n".join(blocks), claims


def references_block(claims: list[dict], records: dict[str, dict]) -> str:
    cited = list(dict.fromkeys(c["source_key"] for c in claims))
    cited.sort(key=lambda k: int(k[1:]))
    return "\n".join(format_reference({"authors": [], "year": "n.d.", **records[k]}) for k in cited)


def render(text: str, claims: list[dict], records: dict[str, dict]) -> str:
    return f"## Literature review\n\n{text}\n\n## References\n\n{references_block(claims, records)}\n"


def dump_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
