"""The bridge from a topic's literature run to the research loop (Increment 3, "topic (a) carried through the loop").

A literature run leaves a verified section (every claim linked to a quote in a retrieved source) and its retrieval log.
`prepare` turns that into what the loop needs: a `retrieved.jsonl` holding exactly the sources the section cites, with
their keys kept (so `[R5]` in the section is `[R5]` in the paper), plus the loop's own seed references (the parent
method and the model it explains) when the section does not already cite them. The section's text then goes into two
prompts: the ideas stage (what is known and what is not) and the write-up (a short related-work section that restates
the verified claims, cites the same keys, and states no numbers of its own).

Nothing here trusts model text for a reference: the records are the ones the literature run retrieved, or arXiv's own
record for a seed.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from pathlib import Path

from vera.loop import references

CITE = re.compile(r"\[(R\d+)\]")
MAX_TEXT_WORDS = 900


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def section_body(literature_md: str) -> str:
    return literature_md.partition("## References")[0].replace("## Literature review", "").strip()


def prepare(
    run_dir: Path,
    literature_dir: Path,
    fetch: Callable[[list[str]], list[dict]] = references.fetch_arxiv,
    *,
    write: bool = True,
) -> dict:
    """Write `run_dir/retrieved.jsonl` from the literature run in `literature_dir`; return what the prompts use.

    Returns {"run_id", "question", "text", "cited", "added"}: the literature run's id, its confirmed question, the
    section body, the keys the section cites, and the seed references appended (key -> arXiv id). With `write=False`
    (a resumed run, whose log is already there) nothing is fetched or written."""
    scope = json.loads((literature_dir / "scope.json").read_text(encoding="utf-8"))
    text = section_body((literature_dir / "literature.md").read_text(encoding="utf-8"))
    by_key = {r["key"]: r for r in _jsonl(literature_dir / "retrieved.jsonl")}
    cited = sorted(set(CITE.findall(text)), key=lambda k: int(k[1:]))
    unknown = [k for k in cited if k not in by_key]
    if unknown:
        raise ValueError(f"the section cites keys the literature run never retrieved: {unknown}")
    result = {"run_id": literature_dir.name, "question": scope["question"], "text": text, "cited": cited, "added": {}}
    if not write:
        return result
    records = [by_key[k] for k in cited]
    present = {r["id"] for r in records}
    missing = [f"arXiv:{i}" for i in references.SEED_ARXIV_IDS if f"arXiv:{i}" not in present]
    added: dict[str, str] = {}
    if missing:
        stamp = dt.date.today().isoformat()
        number = max(int(k[1:]) for k in by_key) + 1
        for rec in fetch([m.removeprefix("arXiv:") for m in missing]):
            key = f"R{number}"
            number += 1
            records.append({"key": key, "retrieved": stamp, **rec})
            added[key] = rec["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    log = run_dir / "retrieved.jsonl"
    log.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return result | {"added": added}


def for_ideas(lit: dict) -> str:
    """Appended to the ideas prompt: what the verified review says, so ideas are informed by it, not by memory."""
    words = lit["text"].split()
    body = " ".join(words[:MAX_TEXT_WORDS])
    return (
        "\n\nA literature review on the research question below has been checked against its sources. Use it to "
        "choose ideas that address what it says is open or limiting, and do not propose what it says is already "
        "known to fail. It is background only: the Residual MSE above remains the measure.\n"
        f"Research question: {lit['question']}\n\nReview:\n{body}"
    )


def for_write_up(lit: dict) -> str:
    """Appended to the write-up prompt: the review to restate as related work, and what the report must admit."""
    words = lit["text"].split()
    body = " ".join(words[:MAX_TEXT_WORDS])
    return (
        "\n\nA literature review on this research question has been checked against its sources:\n"
        f"Research question: {lit['question']}\n\nReview:\n{body}\n\n"
        "Write a 'Related work' section of at most 250 words that restates only what this review says, citing the "
        "same [Rn] keys it uses. State no number that appears in the review, and do not add any claim of your own. "
        "In Limitations, say plainly which parts of the research question these experiments address and which they "
        "do not, given the datasets and the metric of this report."
    )
