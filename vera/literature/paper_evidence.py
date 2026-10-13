# ruff: noqa: E501
"""Wider evidence for a review paper (RSH-F-14, Increment 6): more papers read in full, more passages per paper.

A review reads the top `READ_TOP` (6) kept papers in full and keeps 5 passages of each. A paper needs more to stand on, so
before it is written this step reads up to `PAPER_READ_TOP` (15) kept papers in full, in the review's rank order, and keeps
up to `PAPER_PASSAGES_PER_PAPER` (10) passages of each, ranked by the same BM25 query the review used.

The result is a **superset** of the review's evidence: `paper/passages.jsonl` starts with every passage of the review's
`passages.jsonl`, unchanged and in order, then adds the new ones. Passage ids are deterministic (`R10-P3` is the third
passage built from R10's parse), and BM25 ranking is stable, so a passage the review quoted keeps its id and every review
claim still verifies against the paper's evidence. Nothing is searched again: the kept papers are the review's.

PDFs and parses are cached (`PdfFetcher`, `ParseCache`), so papers the review already read cost no new request. A fetch or
parse failure falls back to the abstract, and the report says why. The frozen `reading` module is used, not changed.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from vera.literature import reading

PAPER_READ_TOP = 15
PAPER_PASSAGES_PER_PAPER = 10
PAPER_DIR = "paper"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def review_query(run_dir: Path) -> str:
    """The BM25 query the review's read stage used: the confirmed question and the search queries."""
    scope = json.loads((run_dir / "scope.json").read_text(encoding="utf-8"))
    queries = json.loads((run_dir / "artifacts" / "queries.json").read_text(encoding="utf-8"))
    qs = queries.get("queries", queries) if isinstance(queries, dict) else queries
    return f"{scope['question']} {' '.join(qs)}"


def widen(
    run_dir: Path,
    fetch: Callable[[str], bytes | None],
    parse: Callable[[bytes], list[tuple[str, str]]],
    *,
    read_top: int = PAPER_READ_TOP,
    per_paper: int = PAPER_PASSAGES_PER_PAPER,
    query: str | None = None,
) -> dict:
    """Write `paper/passages.jsonl` and `paper/reading.json` for a finished review; return the reading summary."""
    query = query if query is not None else review_query(run_dir)
    records = {r["key"]: r for r in _jsonl(run_dir / "retrieved.jsonl")}
    review = _jsonl(run_dir / "passages.jsonl")
    kept = [
        p["key"] for p in json.loads((run_dir / "artifacts" / "reading.json").read_text(encoding="utf-8"))["papers"]
    ]
    passages = list(review)
    have = {p["id"] for p in passages}
    report, full = [], 0
    for key in kept:
        rec = records[key]
        entry = {"key": key, "title": rec["title"], "mode": "abstract"}
        if full < read_top and rec.get("pdf_url"):
            started = time.monotonic()
            try:
                pdf = fetch(rec["pdf_url"])
                if pdf is None:
                    entry["reason"] = f"no PDF: {getattr(fetch, 'last_error', None) or 'unavailable'}"
                else:
                    best = reading.rank_passages(reading.build_passages(parse(pdf), key), query, top=per_paper)
                    if best:
                        new = [p for p in best if p["id"] not in have]
                        passages += new
                        have.update(p["id"] for p in new)
                        entry |= {"mode": "fulltext", "n_new": len(new)}
                        full += 1
                    else:
                        entry["reason"] = "the parser returned no usable body text"
            except Exception as exc:  # noqa: BLE001 - a parser or network failure falls back to the abstract
                entry["reason"] = f"{type(exc).__name__}: {str(exc)[:120]}"
            entry["seconds"] = round(time.monotonic() - started, 1)
        entry["n_passages"] = sum(1 for p in passages if p["source_key"] == key)
        report.append(entry)
    out = run_dir / PAPER_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "passages.jsonl").write_text(
        "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in passages), encoding="utf-8"
    )
    summary = {"n_full_text": full, "n_abstract_only": len(kept) - full, "n_passages": len(passages),
               "n_review_passages": len(review), "n_new_passages": len(passages) - len(review),
               "read_top": read_top, "per_paper": per_paper}  # fmt: skip
    (out / "reading.json").write_text(
        json.dumps(summary | {"papers": report}, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return summary
