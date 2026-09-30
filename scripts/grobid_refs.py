"""Structured reference lists for the benchmark's citation task (Increment 1, T3: GROBID for references).

Sends every generated paper in data/corpus_inventory.csv to GROBID and writes
its reference list, one entry per biblStruct, to the git-ignored
data/cache/bench/refs/<paper>.json:

  [{"n": 1, "title": ..., "authors": [...], "venue": ..., "year": ..., "text": "<as t3_parse formats it>"}]

Existing files are kept unless --force. The benchmark generator
(scripts/build_benchmark.py) reads these files; it never calls GROBID.

Usage: uv run python scripts/grobid_refs.py [--force]
       GROBID must be running (see data/t3_scoring_guide.md or docs/04 T3):
       docker run -d --name vera-grobid -p 8070:8070 lfoppiano/grobid:0.8.2
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "corpus_inventory.csv"
OUT = ROOT / "data" / "cache" / "bench" / "refs"
GROBID = "http://localhost:8070/api/processReferences"
TEI = {"t": "http://www.tei-c.org/ns/1.0"}


def tei_text(el: ET.Element | None) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def entry(n: int, b: ET.Element) -> dict:
    authors = []
    for a in b.findall(".//t:author/t:persName", TEI):
        first = " ".join(tei_text(f) for f in a.findall("t:forename", TEI))
        authors.append(f"{first} {tei_text(a.find('t:surname', TEI))}".strip())
    analytic = b.find("t:analytic/t:title", TEI)
    title = tei_text(analytic) or tei_text(b.find("t:monogr/t:title", TEI))
    venue = tei_text(b.find("t:monogr/t:title", TEI)) if analytic is not None else ""
    date = b.find(".//t:imprint/t:date", TEI)
    year = (date.get("when") or tei_text(date))[:4] if date is not None else ""
    text = ". ".join(p for p in [", ".join(authors), title, venue, year] if p)
    return {"n": n, "title": title, "authors": authors, "venue": venue, "year": year, "text": text}


def references(pdf: Path) -> list[dict]:
    boundary = "----vera-refs"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="input"; filename="{pdf.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + pdf.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        GROBID, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    for attempt in range(3):  # this machine has intermittent network failures, even to localhost
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                root = ET.fromstring(resp.read().decode("utf-8"))
            break
        except (urllib.error.URLError, ConnectionError):
            if attempt == 2:
                raise
            time.sleep(5)
    return [entry(i, b) for i, b in enumerate(root.findall(".//t:listBibl/t:biblStruct", TEI), 1)]


def slug(paper_id: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in paper_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="re-extract papers that already have a file")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with INVENTORY.open(encoding="utf-8", newline="") as f:
        papers = [r["gen_paper_id"] for r in csv.DictReader(f)]
    for paper_id in papers:
        out = OUT / f"{slug(paper_id)}.json"
        if out.exists() and not args.force:
            continue
        pdf = ROOT / "data" / "raw" / "scientisttwo" / f"{paper_id}.pdf"
        t0 = time.perf_counter()
        refs = references(pdf)
        out.write_text(json.dumps({"paper": paper_id, "refs": refs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{time.perf_counter() - t0:5.1f}s refs={len(refs):3} {paper_id}", flush=True)


if __name__ == "__main__":
    main()
