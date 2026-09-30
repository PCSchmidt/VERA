"""Check each parent's venue against OpenReview (Increment 0, inventory evidence).

`parent_venue` comes from one source, ScientistTwo's appendix (Tables 12-14).
An arXiv PDF's first page often still says "preprint" after acceptance, so it
can't confirm the venue. OpenReview records the venue of accepted papers at
NeurIPS 2025, ICLR 2026 and ICML 2026, so this script searches it by exact
title and writes what it reports to `venue_seen` in data/parent_papers.csv.

Reports, for the parents used in the inventory: confirmed (OpenReview venue
names the same conference and year), mismatch, or not found.

Usage: uv run python scripts/verify_venues.py [--delay 2]
"""

from __future__ import annotations

import argparse
import csv
import re
import time
import urllib.error
import urllib.parse
from pathlib import Path

from resolve_parents import FIELDS, OPENREVIEW_API, OUT, get, parse_openreview, similarity

ROOT = Path(__file__).resolve().parents[1]


def same_venue(recorded: str, seen: str) -> bool:
    """'ICML 2026 (spotlight)' vs 'ICML 2026 spotlight' -> True: same conference and year."""
    key = lambda v: re.findall(r"(NeurIPS|ICLR|ICML)\s*(\d{4})", v, re.IGNORECASE)[:1]  # noqa: E731
    a, b = key(recorded), key(seen)
    return bool(a) and bool(b) and a[0][0].lower() == b[0][0].lower() and a[0][1] == b[0][1]


def openreview_venues(title: str) -> list[str]:
    """Venues of every OpenReview note whose title matches, conference records first.

    OpenReview also mirrors arXiv preprints from DBLP (venue 'CoRR'); those say nothing about
    acceptance, so a conference record is preferred when both exist.
    """
    query = urllib.parse.urlencode({"term": title, "type": "terms", "content": "title", "limit": 10})
    notes = [n for n in parse_openreview(get(OPENREVIEW_API + query)) if similarity(title, n["title"]) >= 0.9]
    venues = [n["venue"] for n in notes if n["venue"]]
    return sorted(set(venues), key=lambda v: bool(re.match(r"CoRR", v)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between OpenReview requests")
    args = parser.parse_args()

    with OUT.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with (ROOT / "data" / "corpus_inventory.csv").open(encoding="utf-8", newline="") as f:
        used = {r["parent_title"]: r["gen_paper_id"] for r in csv.DictReader(f)}
    confirmed, mismatch, missing = [], [], []
    for row in rows:
        title = row["parent_title"]
        if title not in used:
            continue
        if not row["venue_seen"] or row["venue_seen"].startswith("CoRR"):
            time.sleep(args.delay)
            try:
                venues = openreview_venues(title)
            except (urllib.error.URLError, TimeoutError, ValueError) as err:
                print(f"LOOKUP FAILED ({err}): {title[:60]}")
                continue
            row["venue_seen"] = venues[0] if venues else ""
        seen = row["venue_seen"]
        if not seen:
            missing.append(title)
        elif same_venue(row["parent_venue"], seen):
            confirmed.append(title)
        else:
            mismatch.append(f"{used[title]}: recorded {row['parent_venue']!r}, OpenReview {seen!r}")
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"parents used: {len(used)}; confirmed {len(confirmed)}, mismatch {len(mismatch)}, not found {len(missing)}")
    for line in mismatch:
        print(f"MISMATCH {line}")
    for title in missing:
        print(f"NOT FOUND {title}")


if __name__ == "__main__":
    main()
