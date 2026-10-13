# ruff: noqa: E501
"""A review paper made from a finished review (RSH-F-12, Increment 6): prompts, record sections and the document.

The paper has four kinds of section (docs/03 0.12, `PaperSection.kind`):

- **evidence**: the introduction and one findings section per theme. The model drafts them as the review's synthesis
  does, sentence by sentence with a claim and a verbatim quote, and they go through the same checks
  (`synthesis_stage.verify_sentences`); VERA adds the `[Rn]` markers and the reference list.
- **record**: *Method* and *Threats to validity*, written here from the run's own files (the review's retrieval
  statistics, the wider reading's report, the ledger). No model writes a word or a number of them.
- **interpretation** and **summary**: added by the interpretation stage (`paper_interpret`).

Claim ids `C1`... are given in reading order across the whole paper, so interpretation can name its premises.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from vera.literature import anchoring, reading, synthesis
from vera.schemas import ClaimLink, PaperSection, RetrievalStats

SYSTEM = (
    "You are a careful research writer drafting a review paper. You say only what the supplied passages support, and "
    "you reply only with what is asked, in the requested format."
)
MIN_THEMES, MAX_THEMES = 3, 6
THEME_PASSAGES = 30  # passages shown to the writer for one findings section
MIN_THEME_PASSAGES, MIN_THEME_SOURCES = 2, 2
INTRO_SHARE, FINDINGS_SHARE = 0.15, 0.60  # of the requested length; interpretation and the abstract take the rest
INTRO = "Introduction"
METHOD = "Method"
THREATS = "Threats to validity"
_WORD = re.compile(r"[a-z0-9]+")


def outline_prompt(
    question: str, review_text: str, records: dict[str, dict], passages: list[dict], emphasis: str | None
) -> str:
    counts: dict[str, int] = {}
    for p in passages:
        counts[p["source_key"]] = counts.get(p["source_key"], 0) + 1
    sources = "\n".join(f"[{k}] {records[k]['title']} ({records[k].get('year') or 'n.d.'}): {n} passages"
                        for k, n in counts.items())  # fmt: skip
    return (
        f"Research question: {question}\n\n"
        f"A short literature review already answers it:\n\n{review_text}\n\n"
        f"The evidence available for a longer review paper comes from these sources:\n{sources}\n\n"
        f"Plan the findings part of a review paper on the question: a title, and {MIN_THEMES} to {MAX_THEMES} themes, "
        "each one a findings section that the evidence can support (a category of information, a kind of method, a "
        "limitation the sources report). For each theme give a heading and 5 to 10 focus words that passages on it "
        "would contain."
        + (f"\n\nThe reader asked for this emphasis: {emphasis}" if emphasis else "")
        + '\n\nReply with JSON: {"title": "...", "themes": [{"heading": "...", "focus": "word word ..."}, ...]}.'
    )


def parse_outline(data: object) -> tuple[str | None, list[dict]]:
    if not isinstance(data, dict):
        return None, []
    title = str(data.get("title") or "").strip() or None
    themes = []
    for t in data.get("themes") or []:
        if isinstance(t, dict) and str(t.get("heading") or "").strip():
            themes.append({"heading": str(t["heading"]).strip(), "focus": str(t.get("focus") or "").strip()})
    return title, themes[:MAX_THEMES]


def theme_passages(theme: dict, passages: list[dict], k: int = THEME_PASSAGES) -> list[dict]:
    """The passages that bear on a theme: BM25 over all the paper's passages, keeping only those that share a word of
    the theme's heading or focus (no model call)."""
    query = f"{theme['heading']} {theme['focus']}"
    words = {w for w in _WORD.findall(query.lower()) if len(w) > 3}
    ranked = reading.rank_passages(passages, query, top=len(passages))
    return [p for p in ranked if words & set(_WORD.findall(p["text"].lower()))][:k]


def theme_supported(selected: list[dict]) -> bool:
    return len(selected) >= MIN_THEME_PASSAGES and len({p["source_key"] for p in selected}) >= MIN_THEME_SOURCES


def section_prompt(question: str, heading: str, purpose: str, passages: list[dict], records: dict[str, dict], words: int,
                   emphasis: str | None) -> str:  # fmt: skip
    return (
        f"Research question: {question}\n\n"
        f'You are writing the section "{heading}" of a review paper on this question. {purpose} Use only the passages '
        "below, and say plainly where they stop.\n\n"
        "Write it as paragraphs of sentences. For every sentence that attributes a finding, method or statement to a "
        'source, give a "claim": {"source_key": "R3", "passage_id": "R3-P2", "quote": "..."} where the quote is copied '
        "word for word from that passage (at least 25 characters, no ellipsis). Do not write citation markers "
        "yourself; they are added from the claims. A sentence that attributes nothing (a transition) has "
        '"claim": null and must not name a source, an author or a system. One claim per sentence, one source per claim. '
        f"About {words} words."
        + (f" The reader asked for this emphasis: {emphasis}" if emphasis else "")
        + '\n\nReply with JSON: {"paragraphs": [[{"text": "...", "claim": {...} or null}, ...], ...]}.'
        + anchoring.ANCHOR_RULE
        + f"\n\nEvidence:\n{synthesis.passages_block(passages, records)}"
    )


INTRO_PURPOSE = (
    "Introduce the question: the problem it concerns, why it matters, and the systems and ideas it builds on, as the "
    "sources describe them. Do not summarise the findings yet."
)


def findings_purpose(theme: dict) -> str:
    return f"Report what the sources establish on this theme ({theme['focus']}), where they agree or differ, and what they leave open."


def number_claims(sections: list[dict]) -> list[ClaimLink]:
    """Claim ids C1... in reading order; each section's claims get theirs in place (`section["claims"]`)."""
    out: list[ClaimLink] = []
    for s in sections:
        for c in s.get("claims", []):
            c["id"] = f"C{len(out) + 1}"
            out.append(ClaimLink(id=c["id"], claim=c["claim"], source_key=c["source_key"], quote=c["quote"],
                                 locator=c["locator"], quote_check="pass"))  # fmt: skip
    return out


# ── record sections: VERA's words and the run's numbers ─────────────────────────────────────────────────


def models_used(ledger_path: Path) -> dict[str, str]:
    """component -> model, from the run's ledger (what actually answered, not what was configured)."""
    out: dict[str, str] = {}
    if ledger_path.exists():
        for ln in ledger_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                out.setdefault(r["component"], r.get("model") or r["backend"])
    return out


def method_section(question: str, stats: RetrievalStats, reading_summary: dict, n_claims: int, n_cited: int,
                   models: dict[str, str]) -> str:  # fmt: skip
    writers = sorted({m for c, m in models.items() if c.startswith("p3.")})
    judges = sorted({m for c, m in models.items() if c.startswith("p2.")})
    queries = "; ".join(f"“{q}”" for q in stats.queries)
    return (
        f"The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: {question}\n\n"
        f"Search. {len(stats.queries)} queries were sent to the paper-search services: {queries}. They retrieved "
        f"{stats.n_retrieved} candidate papers. A relevance screen, judged on titles and abstracts, kept {stats.n_kept} "
        f"and set aside {stats.n_dropped_by_screen}.\n\n"
        f"Reading. Every kept paper was read at its abstract; {reading_summary['n_full_text']} were also read in full "
        f"text, and {reading_summary['n_abstract_only']} at the abstract only. This gave {reading_summary['n_passages']} "
        f"evidence passages, the only text the paper may quote.\n\n"
        f"Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes "
        f"something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim "
        f"in its source, and a judge other than the writer checked that the passage supports the sentence and that the "
        f"quote alone states it; sentences that failed were repaired once or removed. {n_claims} claims from "
        f"{n_cited} sources survived. Interpretation sections, where present, rest only on those claims and are "
        f"labelled as such.\n\n"
        f"Models. Written by {', '.join(writers) or 'not recorded'}; judged by {', '.join(judges) or 'not recorded'}."
    )


def threats_section(stats: RetrievalStats, reading_summary: dict) -> str:
    return (
        f"Coverage. The paper rests on what {len(stats.queries)} queries found; the search was not repeated for the "
        f"paper. A finding reported as missing means these searches did not find it, not that it does not exist.\n\n"
        f"Depth of reading. {reading_summary['n_abstract_only']} of {reading_summary['n_full_text'] + reading_summary['n_abstract_only']} "
        f"kept papers were read at the abstract only, so their methods and caveats are known only as their abstracts "
        f"state them.\n\n"
        "What the checks cover. Each claim was checked against the passage it quotes, not against the whole source or "
        "the wider literature. A claim can be supported by its quote and still leave out a qualification stated "
        "elsewhere in the paper it cites. Interpretation sections were judged to follow from the claims they name; "
        "they were not checked against the sources.\n\n"
        "Same-family grading. The writer is a Claude model; the judges are a different model family, and any "
        "independent scoring of this paper by a Claude model shares the writer's family."
    )


# ── the document ────────────────────────────────────────────────────────────────────────────────────────


def render(title: str, sections: list[PaperSection], claims: list[ClaimLink], records: dict[str, dict]) -> str:
    body = "\n\n".join(f"## {s.heading}\n\n{s.text}" for s in sections)
    refs = synthesis.references_block([c.model_dump() for c in claims], records)
    return f"# {title}\n\n{body}\n\n## References\n\n{refs}\n"
