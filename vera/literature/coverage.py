# ruff: noqa: E501
"""A targeted search for works a paper names (RSH-F-16, Increment 7).

Increment 6's third paper never retrieved the Context Language Models paper that Chris pasted into its emphasis (title,
authors, abstract), and could only say it was missing. Before the paper's evidence is widened, this step reads the
works the confirmed question or the emphasis names, checks whether each is already among the run's sources, and looks
up at most `MAX_LOOKUPS` missing ones through the search client the review used. A work found is added to the paper's
evidence (`paper/added_records.jsonl`, read with the review's records); one that cannot be found is stated in the
threats section. The review's own files are not changed, and the general search is not repeated.

What counts as naming a work, conservatively: a quoted span of at least two words whose first line is a title (an
author line after it, as pasted from a paper's page, gives the first author); an arXiv identifier; "Name et al." or
"Name and colleagues" (the author's surname, searched with the question's words).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from vera.literature import retrieval

MAX_LOOKUPS = 3
FOUND_SIMILARITY = 0.85  # title similarity at which a search hit, or an existing source, is the named work
_QUOTED = re.compile(r"[\"“]([^\"”]{6,2000})[\"”]")
_ARXIV = re.compile(r"\b(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?\b")
_AUTHOR = re.compile(r"\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s+(?:et\s+al\.?|and\s+(?:colleagues|co-?authors))")
_NAME_LIST = re.compile(r"^[A-Z][\w.\-' ]+(?:,\s*[A-Z][\w.\-' ]+){2,}")


def named_targets(*texts: str | None) -> list[dict]:
    """The works the question or the emphasis names: {"kind": "title"|"arxiv"|"author", "query", "title"?, "author"?}."""
    out: list[dict] = []
    seen: set[str] = set()

    def add(t: dict) -> None:
        key = t["query"].casefold()
        if key not in seen:
            seen.add(key)
            out.append(t)

    for text in (t for t in texts if t):
        for m in _QUOTED.finditer(text):
            lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
            title = lines[0].rstrip(".") if lines else ""
            if len(title.split()) < 2 or len(title) > 200:
                continue
            author = None
            if len(lines) > 1 and _NAME_LIST.match(lines[1]):
                author = lines[1].split(",")[0].split()[-1]
            add({"kind": "title", "query": title, "title": title, "author": author})
        for m in _ARXIV.finditer(text):
            add({"kind": "arxiv", "query": m.group(1), "arxiv": m.group(1)})
        for m in _AUTHOR.finditer(text):
            add({"kind": "author", "query": m.group(1), "author": m.group(1)})
    return out


def _matches(target: dict, record: dict) -> bool:
    if target["kind"] == "arxiv":
        return target["arxiv"] in (record.get("id") or "") or target["arxiv"] in (record.get("url") or "")
    if target["kind"] == "title":
        return retrieval.title_similarity(target["title"], record.get("title") or "") >= FOUND_SIMILARITY
    surname = target["author"].casefold()
    return any(surname in str(a).casefold() for a in record.get("authors") or [])


def lookup(
    targets: list[dict], records: dict[str, dict], search: Callable[[str], list[dict]] | None, *, question: str = "",
    limit: int = MAX_LOOKUPS,
) -> tuple[list[dict], list[dict]]:  # fmt: skip
    """(report, added records). Each target is "already a source" (and which), "found" (a new record, keyed after the
    run's last key), "not found", or "not searched" (past the limit, or no search client). Author-only targets are
    searched with the question's words, and only a hit by that author counts."""
    report, added, searched = [], [], 0
    next_key = max((int(k[1:]) for k in records if k[1:].isdigit()), default=0) + 1
    for t in targets:
        have = next((k for k, r in records.items() if _matches(t, r)), None)
        if have:
            report.append({**t, "outcome": "already a source", "key": have})
            continue
        if search is None or searched >= limit:
            report.append({**t, "outcome": "not searched", "why": "no search client" if search is None else f"limit of {limit} lookups"})
            continue
        searched += 1
        query = t["query"] if t["kind"] != "author" else f"{t['author']} {question}"[:200]
        try:
            hits = search(query)
        except Exception as exc:  # noqa: BLE001 - a search failure is reported, not fatal
            report.append({**t, "outcome": "not found", "why": f"search failed: {type(exc).__name__}"})
            continue
        hit = next((h for h in hits if _matches(t, h)), None)
        if hit is None:
            report.append({**t, "outcome": "not found", "why": f"{len(hits)} results, none the named work"})
            continue
        key = f"R{next_key}"
        next_key += 1
        record = {**hit, "key": key, "found_by": "targeted search (RSH-F-16)"}
        added.append(record)
        report.append({**t, "outcome": "found", "key": key, "found_title": hit.get("title")})
    return report, added


def write(out_dir: Path, report: list[dict], added: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coverage.json").write_text(json.dumps({"targets": report}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out_dir / "added_records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in added), encoding="utf-8")


def records(run_dir: Path) -> list[dict]:
    """The review's retrieved records and any the paper's targeted search added (the review's file is not changed)."""
    path = run_dir / "retrieved.jsonl"
    review = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()] if path.exists() else []
    return review + added_records(run_dir / "paper")


def added_records(out_dir: Path) -> list[dict]:
    path = out_dir / "added_records.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def threats_note(out_dir: Path, reading: dict | None = None) -> str:
    """The threats section's sentences on the targeted search, from `paper/coverage.json` and the reading report."""
    path = out_dir / "coverage.json"
    if not path.exists():
        return ""
    targets = json.loads(path.read_text(encoding="utf-8"))["targets"]
    if not targets:
        return ""
    modes = {p["key"]: p.get("mode") for p in (reading or {}).get("papers", [])}
    parts = []
    for t in targets:
        name = f"“{t.get('title') or t['query']}”" if t["kind"] == "title" else (f"arXiv {t['arxiv']}" if t["kind"] == "arxiv" else f"work by {t['author']}")
        if t["outcome"] == "already a source":
            parts.append(f"{name} was already among the review's sources ({t['key']})")
        elif t["outcome"] == "found":
            how = "read in full" if modes.get(t["key"]) == "fulltext" else "read at its abstract only"
            parts.append(f"{name} was found by a targeted search and {how} ({t['key']})")
        elif t["outcome"] == "not found":
            parts.append(f"{name} was searched for and not found ({t.get('why', 'no match')}), so this paper says nothing about it from its own text")
        else:
            parts.append(f"{name} was not searched for ({t.get('why')})")
    return "Works named in the question or the reader's emphasis: " + "; ".join(parts) + "."
