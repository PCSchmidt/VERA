"""Camera-ready parent versions and venue evidence from the papers themselves (Increment 0).

Why: spot-check round 1 (data/inventory_spotcheck_round1.csv) found that an
arXiv preprint can lack what the accepted version has (a code link added at
camera-ready), and that venue claims were backed only by ScientistTwo's
appendix plus metadata this pipeline wrote. This script:

1. downloads the PMLR camera-ready PDF of every ICML 2026 parent used in the
   inventory (proceedings.mlr.press/v306, matched by title) to
   data/raw/parents/pmlr306_<id>.pdf, with provenance;
2. for every parent used, looks for the venue statement the camera-ready
   template prints on page 1 or 2 ("Proceedings of the 43rd International
   Conference on Machine Learning", "39th Conference on Neural Information
   Processing Systems (NeurIPS 2025)", "Published as a conference paper at
   ICLR 2026"), preferring the camera-ready file;
3. adopts camera-ready PDFs saved by hand from OpenReview (which refuses
   scripted downloads) for the parents listed in data/camera_ready_manual.csv:
   any unrecorded PDF in data/raw/parents/ whose page 1 carries the title is
   renamed camera_<forum>.pdf and recorded with its OpenReview URL;
4. where no PDF states it, falls back to the arXiv record's author-written
   comment or journal-ref field.

Writes data/parent_versions.csv (committed): parent_title, parent_venue,
camera_ready_pdf, venue_evidence (quoted), evidence_source.

Usage: uv run --group corpus python scripts/camera_ready.py [--delay 2]
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf
from fetch_corpus import download
from map_parents import squash
from resolve_parents import ARXIV_API, ATOM, get, similarity

from vera import provenance

ROOT = Path(__file__).resolve().parents[1]
PMLR_INDEX = "https://proceedings.mlr.press/v306/"
OUT = ROOT / "data" / "parent_versions.csv"
MANUAL = ROOT / "data" / "camera_ready_manual.csv"
RAW = ROOT / "data" / "raw" / "parents"
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}
STATEMENTS = {
    # ordinals are superscripts, which text extraction often splits: "43 rd", "39 th"
    "ICML 2026": r"Proceedings of the 43\s*rd International Conference on Machine Learning[^.]*",
    "NeurIPS 2025": r"39\s*th Conference on Neural Information Processing Systems \(NeurIPS 2025\)[^.]*",
    "ICLR 2026": r"Published as a conference paper at ICLR 2026",
}
FIELDS = ["parent_title", "parent_venue", "camera_ready_pdf", "venue_evidence", "evidence_source"]


def pmlr_papers(page: str) -> list[tuple[str, str]]:
    """(title, pdf url) for every paper on a PMLR volume index page."""
    out = []
    for block in re.findall(r'<div class="paper">(.*?)</div>', page, re.S):
        title = re.search(r'<p class="title">(.*?)</p>', block, re.S)
        pdf = re.search(r'href="([^"]+\.pdf)"', block)
        if title and pdf:
            out.append((html.unescape(" ".join(title.group(1).split())), pdf.group(1)))
    return out


def venue_statement(pdf: Path, venue: str) -> str:
    """The venue sentence the camera-ready template prints, if it's on page 1 or 2."""
    key = venue.split(" (")[0]
    with pymupdf.open(pdf) as doc:
        text = " ".join(doc[i].get_text() for i in range(min(2, len(doc))))
    match = re.search(STATEMENTS.get(key, r"$^"), re.sub(r"\s+", " ", text))
    return match.group(0).strip() if match else ""


def arxiv_venue_note(arxiv_id: str) -> str:
    feed = ET.fromstring(get(ARXIV_API + urllib.parse.urlencode({"id_list": arxiv_id})))
    entry = feed.find("a:entry", ATOM)
    if entry is None:
        return ""
    notes = [entry.findtext(f"arxiv:{k}", default="", namespaces=ARXIV_NS) for k in ("journal_ref", "comment")]
    return " | ".join(" ".join(n.split()) for n in notes if n.strip())


def adopt_manual(records: dict[str, dict[str, str]]) -> dict[str, str]:
    """Hand-saved camera-ready PDFs: {parent title: repo-relative path}, recorded with provenance."""
    if not MANUAL.exists():
        return {}
    with MANUAL.open(encoding="utf-8", newline="") as f:
        wanted = list(csv.DictReader(f))
    adopted = {}
    for w in wanted:
        dest = RAW / f"camera_{w['forum']}.pdf"
        if not dest.exists():
            for pdf in RAW.glob("*.pdf"):
                if pdf.relative_to(ROOT).as_posix() in records:
                    continue
                with pymupdf.open(pdf) as doc:
                    first = doc[0].get_text() if len(doc) else ""
                if squash(w["parent_title"])[:60] in squash(first):
                    pdf.rename(dest)
                    print(f"adopted {pdf.name} -> {dest.name}")
                    break
        if dest.exists():
            rel = dest.relative_to(ROOT).as_posix()
            if rel not in records:
                records[rel] = provenance.record(ROOT, dest, w["url"])
            adopted[w["parent_title"]] = rel
        else:
            print(f"waiting for a hand-saved PDF of: {w['parent_title'][:70]} ({w['url']})")
    return adopted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between requests")
    args = parser.parse_args()

    with (ROOT / "data" / "parent_papers.csv").open(encoding="utf-8", newline="") as f:
        parents = {r["parent_title"]: r for r in csv.DictReader(f)}
    with (ROOT / "data" / "corpus_inventory.csv").open(encoding="utf-8", newline="") as f:
        used = sorted({r["parent_title"] for r in csv.DictReader(f)})
    records = provenance.load(ROOT)
    manual = adopt_manual(records)
    pmlr = pmlr_papers(get(PMLR_INDEX))
    print(f"PMLR v306 index: {len(pmlr)} papers")

    rows = []
    for title in used:
        p = parents[title]
        venue, camera, evidence, source = p["parent_venue"], "", "", ""
        if venue.startswith("ICML 2026"):
            hits = sorted(((similarity(title, t), t, u) for t, u in pmlr if squash(t)[:12] == squash(title)[:12]),
                          reverse=True)  # fmt: skip
            if hits and hits[0][0] >= 0.9:
                url = hits[0][2]
                dest = RAW / f"pmlr306_{Path(urllib.parse.urlparse(url).path).stem}.pdf"
                rel = dest.relative_to(ROOT).as_posix()
                if not (provenance.is_current(ROOT, dest, records) and records[rel]["url"] == url):
                    time.sleep(args.delay)
                    download(url, dest)
                    records[rel] = provenance.record(ROOT, dest, url)
                camera = rel
            else:
                print(f"NOT IN PMLR v306: {title[:70]}")
        camera = camera or manual.get(title, "")
        for pdf in [camera, p["pdf_path"]]:
            if pdf and not evidence:
                evidence = venue_statement(ROOT / pdf, venue)
                source = pdf if evidence else ""
        if not evidence and p["source"] == "arxiv":
            time.sleep(args.delay)
            note = arxiv_venue_note(p["paper_id"])
            if re.search(venue.split(" (")[0].replace(" ", r"\s*"), note, re.I):
                evidence, source = note, f"arXiv {p['paper_id']} record (author comment/journal-ref)"
        rows.append({"parent_title": title, "parent_venue": venue, "camera_ready_pdf": camera,
                     "venue_evidence": evidence, "evidence_source": source})  # fmt: skip
        print(f"{'OK ' if evidence else '-- '} {venue[:12]:12} {title[:60]}", flush=True)

    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    have = sum(bool(r["venue_evidence"]) for r in rows)
    print(f"{len(rows)} parents: camera-ready from PMLR {sum(bool(r['camera_ready_pdf']) for r in rows)}, "
          f"venue stated in the paper or arXiv record {have}, missing {len(rows) - have}")  # fmt: skip


if __name__ == "__main__":
    main()
