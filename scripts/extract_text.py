"""Extract plain text from downloaded corpus PDFs for inventory work (Increment 0, tasks 4-6).

Writes data/cache/text/<same relative path>.txt (git-ignored: derived from
corpus papers, so never committed). Pages are separated by form feeds and
prefixed with `=== page N ===` so notes can cite a page.

This is plain PyMuPDF text, enough to find a paper's baseline, parent
citation, code links and experimental setup. It is not the trade T3 parser
decision, which scores reference and table extraction separately.

Usage: uv run --group corpus python scripts/extract_text.py [glob ...]
       (default: every PDF under data/raw/; existing, newer text is skipped)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache" / "text"


def text_path(pdf: Path) -> Path:
    return CACHE / pdf.relative_to(RAW).with_suffix(".txt")


def extract(pdf: Path) -> str:
    with pymupdf.open(pdf) as doc:
        return "\f".join(f"=== page {n} ===\n{page.get_text()}" for n, page in enumerate(doc, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("globs", nargs="*", default=["**/*.pdf"], help="globs relative to data/raw/")
    parser.add_argument("--force", action="store_true", help="re-extract even if the text is newer")
    args = parser.parse_args()

    pdfs = sorted({p for g in args.globs for p in RAW.glob(g) if p.suffix == ".pdf"})
    if not pdfs:
        sys.exit("no PDFs matched under data/raw/")
    done = skipped = 0
    for pdf in pdfs:
        out = text_path(pdf)
        if not args.force and out.exists() and out.stat().st_mtime >= pdf.stat().st_mtime:
            skipped += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(extract(pdf), encoding="utf-8")
        done += 1
    print(f"extracted {done}, up to date {skipped}, into {CACHE.relative_to(ROOT).as_posix()}/")


if __name__ == "__main__":
    main()
