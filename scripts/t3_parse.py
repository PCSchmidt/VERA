"""Trade T3 (PDF parser): parse the sample papers with each candidate parser (Increment 0).

Candidates (docs/04 T3):
  pymupdf4llm  PyMuPDF's Markdown mode, with table detection (pip only)
  grobid       GROBID 0.8.2 in Docker (CRF models), TEI with structured references
  docling      Docling (IBM), Markdown with a table-structure model (pip; torch)
An LLM-based parser is not tested (spend ceiling); see docs/04.

For each sample paper (data/t3_sample.json) and parser, writes to the
git-ignored data/cache/t3/<paper>/:
  <parser>.md          full output as Markdown (GROBID: text rebuilt from TEI)
  <parser>_refs.txt    the reference list as the parser delivers it, one entry per block
  <parser>_tables.md   every table the parser found, in order, with its caption if any

and records automatic measures in data/t3_auto.csv (committed): seconds,
references extracted, tables found. Correctness is scored by hand
(data/t3_scores.csv), not here: the parser comparison is not self-graded.

Usage: uv run --group t3 python scripts/t3_parse.py [--parsers pymupdf4llm grobid docling]
       GROBID must be running: docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.2
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "t3_sample.json"
OUT = ROOT / "data" / "cache" / "t3"
AUTO = ROOT / "data" / "t3_auto.csv"
GROBID = "http://localhost:8070/api/processFulltextDocument"
TEI = {"t": "http://www.tei-c.org/ns/1.0"}
REF_WORD = re.compile(r"\bREFERENCES\w*|^#{1,6}\s*\**\s*References\b|^\s*References\s*$|\d+\*\*\s+References\b")
APPENDIX = re.compile(r"^#{1,6}\s*\**\s*(appendix|A\s+[A-Z])|^\**\s*APPENDIX\b|^\**\s*A\s+[A-Z]{3,}")


# ── Markdown helpers (shared by the Markdown parsers) ─────────────────────────


def md_references(md: str) -> list[str]:
    """Blocks after the references heading, as the parser delivered them, up to the appendix.

    The ICLR template's heading is an uppercase REFERENCES, which some parsers emit mid-line or
    garbled ("REFERENCESEFERENCES"), so match the word rather than a whole Markdown heading line.
    """
    lines = [line.lstrip("> ").rstrip() for line in md.splitlines()]
    start = None
    for i, line in enumerate(lines):
        match = REF_WORD.search(line)
        if match:
            start, lines[i] = i, line[match.end() :]
            break
    if start is None:
        return []
    blocks, cur = [], []
    for line in lines[start:]:
        s = line.strip()
        if APPENDIX.match(s):
            break
        if not s or (s.startswith(("- ", "* ")) and cur):  # blank lines and list items separate entries
            if cur:
                blocks.append(" ".join(cur))
                cur = []
            if not s:
                continue
        cur.append(s.lstrip("-* ").strip())
    if cur:
        blocks.append(" ".join(cur))
    return [b for b in blocks if len(b) > 15]


def md_tables(md: str) -> list[str]:
    """Pipe tables in order, each with the non-empty line before it (often the caption)."""
    lines, tables, i = md.splitlines(), [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            before = next((lines[k].strip() for k in range(i - 1, max(i - 4, -1), -1) if lines[k].strip()), "")
            tables.append(f"<!-- context: {before[:200]} -->\n" + "\n".join(lines[i:j]))
            i = j
        else:
            i += 1
    return tables


# ── parsers ───────────────────────────────────────────────────────────────────


def run_pymupdf4llm(pdf: Path) -> tuple[str, list[str], list[str]]:
    import pymupdf4llm

    md = pymupdf4llm.to_markdown(str(pdf), show_progress=False, use_ocr=False)  # born-digital PDFs
    return md, md_references(md), md_tables(md)


_docling = None


def run_docling(pdf: Path) -> tuple[str, list[str], list[str]]:
    global _docling
    from docling.document_converter import DocumentConverter

    if _docling is None:
        _docling = DocumentConverter()
    doc = _docling.convert(str(pdf)).document
    md = doc.export_to_markdown()
    tables = []
    for t in doc.tables:
        caption = t.caption_text(doc) if hasattr(t, "caption_text") else ""
        tables.append(f"<!-- caption: {caption[:200]} -->\n" + t.export_to_markdown(doc))
    return md, md_references(md), tables


def tei_text(el: ET.Element | None) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def format_bibl(b: ET.Element) -> str:
    """A TEI biblStruct as 'Authors. Title. Venue, year.' so it reads like the PDF entry."""
    names = []
    for a in b.findall(".//t:author/t:persName", TEI):
        first = " ".join(tei_text(f) for f in a.findall("t:forename", TEI))
        names.append(f"{first} {tei_text(a.find('t:surname', TEI))}".strip())
    title = tei_text(b.find("t:analytic/t:title", TEI)) or tei_text(b.find("t:monogr/t:title", TEI))
    venue = tei_text(b.find("t:monogr/t:title", TEI)) if b.find("t:analytic/t:title", TEI) is not None else ""
    date = b.find(".//t:imprint/t:date", TEI)
    year = (date.get("when") or tei_text(date))[:4] if date is not None else ""
    ids = [f"{i.get('type')}:{tei_text(i)}" if i.get("type") else tei_text(i) for i in b.findall(".//t:idno", TEI)]
    parts = [", ".join(names), title, venue, year] + ids
    return ". ".join(p for p in parts if p)


def run_grobid(pdf: Path) -> tuple[str, list[str], list[str]]:
    boundary = "----vera-t3"
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
    with urllib.request.urlopen(req, timeout=600) as resp:
        tei = resp.read().decode("utf-8")
    root = ET.fromstring(tei)
    refs = [format_bibl(b) for b in root.findall(".//t:back//t:listBibl/t:biblStruct", TEI)]
    tables = []
    for fig in root.findall(".//t:figure[@type='table']", TEI):
        head = tei_text(fig.find("t:head", TEI)) + " " + tei_text(fig.find("t:figDesc", TEI))
        rows = ["| " + " | ".join(tei_text(c) for c in row.findall("t:cell", TEI)) + " |"
                for row in fig.findall(".//t:table/t:row", TEI)]  # fmt: skip
        tables.append(f"<!-- caption: {head.strip()[:200]} -->\n" + ("\n".join(rows) or "(no cells)"))
    body_text = "\n\n".join(tei_text(p) for p in root.findall(".//t:body//t:p", TEI))
    return body_text, refs, tables


PARSERS = {"pymupdf4llm": run_pymupdf4llm, "grobid": run_grobid, "docling": run_docling}


# ── main ──────────────────────────────────────────────────────────────────────


def slug(paper_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parsers", nargs="+", default=list(PARSERS), choices=list(PARSERS))
    args = parser.parse_args()

    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    auto: dict[tuple[str, str], dict[str, str]] = {}
    if AUTO.exists():
        with AUTO.open(encoding="utf-8", newline="") as f:
            auto = {(r["gen_paper_id"], r["parser"]): r for r in csv.DictReader(f)}
    for name in args.parsers:
        for paper_id in sample["papers"]:
            pdf = ROOT / "data" / "raw" / "scientisttwo" / f"{paper_id}.pdf"
            out = OUT / slug(paper_id)
            out.mkdir(parents=True, exist_ok=True)
            t0 = time.perf_counter()
            try:
                md, refs, tables = PARSERS[name](pdf)
                error = ""
            except Exception as err:  # noqa: BLE001 - a parser failure is a result to record
                md, refs, tables, error = "", [], [], f"{type(err).__name__}: {err}"[:200]
            seconds = time.perf_counter() - t0
            (out / f"{name}.md").write_text(md, encoding="utf-8")
            (out / f"{name}_refs.txt").write_text(
                "\n\n".join(f"[{i}] {r}" for i, r in enumerate(refs, 1)), encoding="utf-8"
            )
            (out / f"{name}_tables.md").write_text(
                "\n\n".join(f"## Table {i}\n\n{t}" for i, t in enumerate(tables, 1)), encoding="utf-8"
            )
            auto[(paper_id, name)] = {
                "gen_paper_id": paper_id, "parser": name, "seconds": f"{seconds:.1f}",
                "refs_extracted": str(len(refs)), "tables_found": str(len(tables)), "error": error,
            }  # fmt: skip
            print(f"{name:12} {seconds:6.1f}s refs={len(refs):3} tables={len(tables):2} {paper_id} {error}", flush=True)
    with AUTO.open("w", encoding="utf-8", newline="") as f:
        fields = ["gen_paper_id", "parser", "seconds", "refs_extracted", "tables_found", "error"]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(auto.values(), key=lambda r: (r["gen_paper_id"], r["parser"])))


if __name__ == "__main__":
    main()
