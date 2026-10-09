"""Claim anchoring and retrieval disclosure (Increment 4, "Literature stage v2").

Increment 3 found a claim's quote can support only part of its sentence while the judge is shown the whole passage, and
that some claim sentences add the review's own comparison or caveat under a source's citation. Two checks and one rule:

- `marker_problem`: a deterministic check for editorial connectives (a contrast, a comparison, an inference) in the
  sentence that the quote does not itself contain;
- `quote_covers_claim`: a judge question shown the quote only (not the passage): does the quote state what the
  sentence claims? Failures go to the repair step with the reason `unanchored`;
- `ANCHOR_RULE`: appended to the synthesis prompt: one assertion per sentence, nothing the quote does not say.

And `retrieval_note` / `insert_note`: the paragraph the review carries about its own retrieval, from the stage's
counts, so a "what is not established" section is read as conditional on what retrieval found (no key-paper figure
exists for a user's topic, so none is claimed).

The audit and synthesis modules the Increment 3 audit froze are not edited here; this file is new.
"""

from __future__ import annotations

import re

from vera.schemas import Question, QuestionType, RetrievalStats

ANCHOR_RULE = (
    "\n\nEach sentence with a claim must make ONE assertion that its quote states, in the quote's own terms. Do not "
    "add a comparison with another source, a contrast, a caveat of your own or an inference ('so', 'which sits oddly "
    "beside', 'but this is for general evaluation') to a sentence that carries a citation: put it in a separate "
    "sentence with no claim, or leave it out. The quote must be the complete sentence (or sentences) of the passage, "
    "copied word for word, that states what your sentence says, not a fragment: someone who reads only the quote "
    "should find the whole assertion in it, including who or what it is about. Name the subject of every sentence "
    "with a claim (the study, the method, the authors): do not start it with 'It', 'They' or 'This', and do not "
    "write 'this advantage' or 'these results' for something a previous sentence said."
)
# editorial connectives: each is fine inside a quote and a problem when only the sentence has it
MARKERS = (
    "unlike", "in contrast", "contrasts with", "sits oddly", "oddly beside", "whereas", "by contrast", "so this",
    "which suggests", "which implies", "this is not", "but this is", "however", "rather than", "in line with",
)  # fmt: skip


def marker_problem(sentence: str, quote: str) -> str | None:
    """The first editorial connective the sentence has and the quote does not, or None."""
    s, q = sentence.lower(), quote.lower()
    return next((m for m in MARKERS if m in s and m not in q), None)


_DANGLING = re.compile(
    r"^\s*(?:it|they|this|these|that|those|its|their|such)\b|\b(?:that|and|but)\s+(?:this|these|those)\s+\w+", re.I
)


_BARE_KEY = re.compile(
    r"(?<![\x5b0-9A-Za-z_])R[0-9]+(?![0-9]|\x5d)"
)  # not in a bracket citation, not inside a longer token


def names_a_source_without_a_claim(sentence: str) -> str | None:
    """A source key in running text ('R12 a much larger set') in a sentence that has no claim behind it, or None.
    Such a sentence says something about a source that no quote supports and the audit never checks."""
    m = _BARE_KEY.search(sentence)
    return m.group(0) if m else None


def dangling_reference(sentence: str) -> str | None:
    """The opening words of a sentence that refers back to a sentence the reader may not have read ('It also reports
    that this advantage grows'), or None. A claim sentence must say whose finding it is."""
    m = _DANGLING.search(sentence)
    return m.group(0).strip() if m else None


def quote_covers_claim(sentence: str, quote: str, title: str | None = None) -> tuple[Question, str]:
    """(question, material): does the quote state what the sentence claims about its source? The judge sees the source's
    title (who the claim is about), the claim and the quote, and not the rest of the passage."""
    source = f'Source: "{title}"\n' if title else ""
    material = f"{source}Claim: {sentence}\n\nQuote from that source: {quote}"
    text = (
        "The claim is about the source named above. Does the quote state what the claim says about it, including any "
        "number, direction and qualifier? Answer false if part of the claim (a comparison with another source, a "
        "contrast, an inference, a second assertion) is not in the quote."
    )
    return Question(id="lit.quote_covers_claim", type=QuestionType.BOOLEAN, text=text), material


def retrieval_note(stats: RetrievalStats) -> str:
    """The section the review carries about its own retrieval, from the stage's counts."""
    n_abstract = max(stats.n_kept - stats.n_read_full, 0)
    return (
        "## Retrieval and its limits\n\n"
        f"This review rests on {len(stats.queries)} search queries, which retrieved {stats.n_retrieved} candidate "
        f"papers. A relevance screen kept {stats.n_kept} and set aside {stats.n_dropped_by_screen}; "
        f"{stats.n_read_full} were read in full text and {n_abstract} at the abstract only. Where this review says "
        "that something is missing or not established, it means that these searches did not find it: it is not a "
        "measure of the literature, and no figure for how much of the field the searches missed is available for a "
        "topic given without a list of its key papers."
    )


def insert_note(markdown: str, note: str) -> str:
    """The review's markdown with the note placed before its reference list (or at the end if it has none)."""
    if note in markdown:
        return markdown
    head, sep, tail = markdown.partition("## References")
    return f"{head.rstrip()}\n\n{note}\n\n{sep}{tail}" if sep else f"{markdown.rstrip()}\n\n{note}\n"


def stats_from_state(state: dict) -> RetrievalStats:
    """The stage's counts from the run's state: queries, retrieved, kept, read in full."""
    report = state.get("read_report") or []
    retrieved, kept = len(state.get("records") or []), len(state.get("kept") or [])
    return RetrievalStats(
        queries=list(state.get("queries") or []), n_retrieved=retrieved, n_kept=kept,
        n_read_full=sum(1 for e in report if e.get("mode") == "fulltext"),
        n_dropped_by_screen=max(retrieved - kept, 0),
    )  # fmt: skip


def has_note(markdown: str) -> bool:
    return re.search(r"^## Retrieval and its limits", markdown, re.MULTILINE) is not None
