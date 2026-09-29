"""Suggest each generated paper's parent paper (Increment 0, task 4).

ScientistTwo's paper (arXiv 2609.19644, Appendix A.1, Tables 12-14) lists the
107 accepted papers whose problems and codebases were its inputs: 38 NeurIPS
2025, 5 ICLR 2026, 64 ICML 2026 spotlights. It does not say which generated
paper came from which input, so this script:

1. parses those tables into data/parent_candidates.csv (committed; titles,
   venue, and the paper's short citation), and
2. searches each generated paper's extracted text (scripts/extract_text.py)
   for every candidate title, writing ranked suggestions to
   data/cache/parent_suggestions.json for review.

A suggestion is evidence, not a verdict: the inventory is filled after the
suggestions are read against the generated paper's own text.

Usage: uv run python scripts/map_parents.py [--refresh]
       (--refresh re-fetches the arXiv HTML; otherwise the cached copy is used)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

from discover_corpus import USER_AGENT

ROOT = Path(__file__).resolve().parents[1]
PAPER_URL = "https://arxiv.org/html/2609.19644"
CACHE = ROOT / "data" / "cache"
PAPER_CACHE = CACHE / "scientisttwo_2609.19644.html"
TEXT = CACHE / "text" / "scientisttwo"
CANDIDATES = ROOT / "data" / "parent_candidates.csv"
SUGGESTIONS = CACHE / "parent_suggestions.json"

TABLES = {"12": "NeurIPS 2025", "13": "ICLR 2026", "14": "ICML 2026 (spotlight)"}
EXPECTED = {"NeurIPS 2025": 38, "ICLR 2026": 5, "ICML 2026 (spotlight)": 64}
_ROW = re.compile(r"^\s*(.+?)\s+\(\s*([^()]+?,\s*\d{4}[a-z]?)\s*\)\s*$")
STOP = set("a an and for of on the to via with in by from at as is are its under through".split())


# ── parsing (pure) ────────────────────────────────────────────────────────────


def html_to_text(page: str) -> str:
    page = re.sub(r"<(script|style|math)[^>]*>.*?</\1>", " ", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", text))


def parse_candidates(text: str) -> list[dict[str, str]]:
    """Rows of Tables 12-14: one per input paper, with its venue."""
    rows, venue = [], None
    for line in text.splitlines():
        table = re.match(r"\s*Table (\d+):", line)
        if table:
            venue = TABLES.get(table.group(1))
            continue
        if rows and re.match(r"\s*A\.2 ", line):  # the table of contents also has an "A.2" line
            break
        match = _ROW.match(line)
        if venue and match:
            rows.append({"parent_title": match.group(1), "parent_venue": venue, "cite": match.group(2)})
    return rows


def squash(text: str) -> str:
    """Lowercase alphanumerics only, with line-end hyphenation undone."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"-\s*\n\s*", "", text).lower())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def short_name(title: str) -> str:
    """The name before a colon ('SVL: Empowering ...' -> 'svl'), or '' if the title has none."""
    head = title.split(":")[0]
    return squash(head) if ":" in title and len(head.split()) <= 2 else ""


def suggest(
    paper_text: str, method_name: str, candidates: list[dict[str, str]], top: int = 3
) -> list[dict[str, object]]:
    """Rank candidates: exact title in the text, then short name in the method name, then rare-word overlap."""
    paper_squashed, paper_words = squash(paper_text), words(paper_text)
    title_words = [words(c["parent_title"]) for c in candidates]
    df: dict[str, int] = {}
    for tw in title_words:
        for w in tw:
            df[w] = df.get(w, 0) + 1
    ranked = []
    for c, tw in zip(candidates, title_words, strict=True):
        title, name = c["parent_title"], short_name(c["parent_title"])
        weight = {w: 1 / df[w] for w in tw}
        overlap = sum(weight[w] for w in tw & paper_words) / (sum(weight.values()) or 1)
        if squash(title) in paper_squashed:
            tier, how = 2, "exact title"
        elif name and len(name) >= 3 and name in squash(method_name):
            tier, how = 1, f"method name contains '{title.split(':')[0]}'"
        else:
            tier, how = 0, "word overlap"
        ranked.append({"parent_title": title, "tier": tier, "overlap": round(overlap, 2), "how": how})
    ranked.sort(key=lambda r: (-r["tier"], -r["overlap"]))
    return ranked[:top]


# ── main ──────────────────────────────────────────────────────────────────────


def load_paper(refresh: bool) -> str:
    if refresh or not PAPER_CACHE.exists():
        req = urllib.request.Request(PAPER_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            PAPER_CACHE.parent.mkdir(parents=True, exist_ok=True)
            PAPER_CACHE.write_bytes(resp.read())
    return PAPER_CACHE.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="re-fetch the arXiv HTML")
    args = parser.parse_args()

    candidates = parse_candidates(html_to_text(load_paper(args.refresh)))
    counts = {v: sum(c["parent_venue"] == v for c in candidates) for v in EXPECTED}
    if counts != EXPECTED:
        sys.exit(f"parsed {counts}, expected {EXPECTED}: the appendix layout changed")
    retrieved = dt.date.fromtimestamp(PAPER_CACHE.stat().st_mtime).isoformat()
    with CANDIDATES.open("w", encoding="utf-8", newline="") as f:
        f.write(f"# source: {PAPER_URL} Appendix A.1 Tables 12-14, retrieved {retrieved}\n")
        writer = csv.DictWriter(f, fieldnames=["parent_title", "parent_venue", "cite"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(candidates)

    discovery = json.loads((ROOT / "data" / "corpus_discovery.json").read_text(encoding="utf-8"))
    out = {}
    for paper in discovery["papers"]:
        text_file = TEXT.joinpath(*paper["file"].split("/")[1:]).with_suffix(".txt")
        if not text_file.exists():
            sys.exit(f"missing {text_file}; run scripts/extract_text.py first")
        out[paper["gen_paper_id"]] = suggest(text_file.read_text(encoding="utf-8"), paper["method_name"], candidates)
    SUGGESTIONS.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    exact = [k for k, v in out.items() if v[0]["tier"] == 2]
    multi = [k for k, v in out.items() if sum(r["tier"] == 2 for r in v) > 1]
    print(f"{len(candidates)} candidates -> {CANDIDATES.relative_to(ROOT).as_posix()}")
    print(f"{len(exact)}/{len(out)} papers cite a candidate title verbatim; {len(multi)} cite more than one")
    print(f"suggestions -> {SUGGESTIONS.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
