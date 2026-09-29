"""Resolve the 107 candidate parent papers and download them (Increment 0, tasks 4-6).

For each row of data/parent_candidates.csv (scripts/map_parents.py):

1. search arXiv by title words; accept a hit only if its title matches the
   candidate's (normalised similarity >= 0.9); PDF from arxiv.org;
2. otherwise search OpenReview (all three venues review there) the same way;
   PDF from openreview.net. OpenReview also reports the venue, which
   cross-checks the appendix table the candidate came from.

PDFs go to data/raw/parents/ with a provenance record (FND-C-02). Results go
to data/parent_papers.csv:

  parent_title, parent_venue, cite, paper_id, source, matched_title, venue_seen, pdf_path

Known arXiv ids the title search misses can be listed, with their source, in
data/parent_arxiv_hints.csv; a hint is used only if its arXiv title matches.

`paper_id` is an arXiv id, `openreview:<forum id>`, or `unknown` (needs a
manual lookup). Polite: arXiv asks for one request per 3 s (--delay 3.5).
Resumable: resolved rows whose PDF still matches its record are skipped, and
a PDF already on disk with a matching record is not downloaded again.

Usage: uv run python scripts/resolve_parents.py [--delay 3.5] [--limit N]
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from discover_corpus import USER_AGENT
from fetch_corpus import download
from map_parents import STOP, squash

from vera import provenance

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "parent_candidates.csv"
OUT = ROOT / "data" / "parent_papers.csv"
HINTS = ROOT / "data" / "parent_arxiv_hints.csv"
RAW = ROOT / "data" / "raw" / "parents"
ARXIV_API = "https://export.arxiv.org/api/query?"
OPENREVIEW_API = "https://api2.openreview.net/notes/search?"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
FIELDS = ["parent_title", "parent_venue", "cite", "paper_id", "source", "matched_title", "venue_seen", "pdf_path"]
MIN_SIMILARITY = 0.9
Hit = tuple[str, str, str, str]  # (paper id, matched title, venue seen, pdf url)


# ── parsing and matching (pure) ───────────────────────────────────────────────


def query_for(title: str) -> str:
    terms = [w for w in re.findall(r"[A-Za-z0-9]+", title) if w.lower() not in STOP and len(w) > 1]
    return " AND ".join(f"ti:{w}" for w in terms[:12])


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, squash(a), squash(b)).ratio()


def best_match(title: str, entries: list[tuple[str, str]]) -> tuple[str, str, float] | None:
    """(id, title, similarity) of the closest entry, if it clears MIN_SIMILARITY."""
    scored = sorted(((i, t, similarity(title, t)) for i, t in entries), key=lambda x: -x[2])
    return scored[0] if scored and scored[0][2] >= MIN_SIMILARITY else None


def parse_feed(xml: str) -> list[tuple[str, str]]:
    """(arXiv id without version, title) per entry of an arXiv Atom feed."""
    root = ET.fromstring(xml)
    out = []
    for entry in root.findall("a:entry", ATOM):
        raw_id = entry.findtext("a:id", default="", namespaces=ATOM)
        title = " ".join(entry.findtext("a:title", default="", namespaces=ATOM).split())
        match = re.search(r"abs/(.+?)(v\d+)?$", raw_id)
        if match:
            out.append((match.group(1), title))
    return out


def parse_openreview(payload: str) -> list[dict[str, str]]:
    notes = json.loads(payload).get("notes", [])
    out = []
    for n in notes:
        c = n.get("content", {})
        title, venue, pdf = ((c.get(k) or {}).get("value") or "" for k in ("title", "venue", "pdf"))
        out.append({"forum": n.get("forum") or n["id"], "title": title, "venue": venue, "pdf": pdf})
    return out


# ── network ───────────────────────────────────────────────────────────────────


def get(url: str, tries: int = 4) -> str:
    """GET with retries and backoff; transient DNS and connection failures are common here."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries - 1:
                raise
            time.sleep(10 * 2**attempt)
    raise AssertionError("unreachable")


def search_arxiv(title: str) -> Hit | None:
    query = urllib.parse.urlencode({"search_query": query_for(title), "max_results": 5})
    hit = best_match(title, parse_feed(get(ARXIV_API + query)))
    if not hit:
        return None
    arxiv_id, matched, _ = hit
    return arxiv_id, matched, "", f"https://arxiv.org/pdf/{arxiv_id}"


def lookup_arxiv_id(title: str, arxiv_id: str) -> Hit | None:
    """A known arXiv id (data/parent_arxiv_hints.csv), accepted only if its title matches."""
    query = urllib.parse.urlencode({"id_list": arxiv_id})
    hit = best_match(title, parse_feed(get(ARXIV_API + query)))
    return (hit[0], hit[1], "", f"https://arxiv.org/pdf/{hit[0]}") if hit else None


def search_openreview(title: str) -> Hit | None:
    query = urllib.parse.urlencode({"term": title, "type": "terms", "content": "title", "limit": 5})
    notes = [n for n in parse_openreview(get(OPENREVIEW_API + query)) if n["pdf"]]
    hit = best_match(title, [(n["forum"], n["title"]) for n in notes])
    if not hit:
        return None
    note = next(n for n in notes if n["forum"] == hit[0])
    pdf = note["pdf"] if note["pdf"].startswith("http") else "https://openreview.net" + note["pdf"]
    return f"openreview:{note['forum']}", note["title"], note["venue"], pdf


def fetch(url: str, dest: Path, records: dict[str, dict[str, str]]) -> None:
    """Download with a provenance record, unless the file is already on disk and recorded."""
    if provenance.is_current(ROOT, dest, records) and records[dest.relative_to(ROOT).as_posix()]["url"] == url:
        return
    download(url, dest)
    records[dest.relative_to(ROOT).as_posix()] = provenance.record(ROOT, dest, url)


# ── main ──────────────────────────────────────────────────────────────────────


def read_candidates() -> list[dict[str, str]]:
    with CANDIDATES.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def save(rows: list[dict[str, str]], pending: list[dict[str, str]]) -> None:
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows + pending)


def unresolved(cand: dict[str, str]) -> dict[str, str]:
    return {**cand, "paper_id": "unknown", "source": "", "matched_title": "", "venue_seen": "", "pdf_path": ""}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=3.5, help="seconds between requests")
    parser.add_argument("--limit", type=int, default=None, help="resolve at most N new rows")
    args = parser.parse_args()

    done: dict[str, dict[str, str]] = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f:
            done = {r["parent_title"]: r for r in csv.DictReader(f) if "paper_id" in r}
    records = provenance.load(ROOT)
    hints: dict[str, str] = {}
    if HINTS.exists():
        with HINTS.open(encoding="utf-8", newline="") as f:
            hints = {r["parent_title"]: r["arxiv_id"] for r in csv.DictReader(f)}
    candidates = read_candidates()
    rows: list[dict[str, str]] = []
    new = 0
    for n, cand in enumerate(candidates):
        prev = done.get(cand["parent_title"])
        if prev and prev["paper_id"] != "unknown" and provenance.is_current(ROOT, ROOT / prev["pdf_path"], records):
            rows.append(prev)
            continue
        if args.limit is not None and new >= args.limit:
            rows.append(prev or unresolved(cand))
            continue
        new += 1
        row, title = unresolved(cand), cand["parent_title"]
        try:
            time.sleep(args.delay)
            hit, source = None, "arxiv"
            if title in hints:
                hit = lookup_arxiv_id(title, hints[title])
            if hit is None:
                if title in hints:
                    time.sleep(args.delay)
                hit = search_arxiv(title)
            if hit is None:
                time.sleep(args.delay)
                hit, source = search_openreview(title), "openreview"
            if hit:
                paper_id, matched, venue_seen, url = hit
                dest = RAW / (re.sub(r"[^A-Za-z0-9.]+", "_", paper_id) + ".pdf")
                time.sleep(args.delay)
                fetch(url, dest, records)
                row.update(paper_id=paper_id, source=source, matched_title=matched, venue_seen=venue_seen,
                           pdf_path=dest.relative_to(ROOT).as_posix())  # fmt: skip
                print(f"[{new}] {source:10} {paper_id} {title[:60]}", flush=True)
            else:
                print(f"[{new}] NO MATCH   {title[:70]}", flush=True)
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            print(f"[{new}] FAILED ({err}); will retry next run: {title[:60]}", flush=True)
            row = prev or row
        rows.append(row)
        save(rows, [done[c["parent_title"]] for c in candidates[n + 1 :] if c["parent_title"] in done])

    save(rows, [])
    by_source = {s: sum(r["source"] == s for r in rows) for s in ("arxiv", "openreview")}
    missing = [r["parent_title"] for r in rows if r["paper_id"] == "unknown"]
    print(f"resolved {len(rows) - len(missing)}/{len(rows)} {by_source} -> {OUT.relative_to(ROOT).as_posix()}")
    for title in missing:
        print(f"UNRESOLVED {title}", file=sys.stderr)


if __name__ == "__main__":
    main()
