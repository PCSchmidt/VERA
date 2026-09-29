"""List the hyperlink targets embedded in corpus PDFs (Increment 0, code availability).

Plain text extraction loses a link whose visible text isn't the URL (e.g. a
footnote reading "Mixture-of-CB-Experts"), so code URLs look missing. This
reads each PDF's link annotations instead and writes
data/cache/pdf_links.json: {"data/raw/<...>.pdf": ["https://...", ...]}.

Usage: uv run --group corpus python scripts/pdf_links.py [glob ...]
       (default: parents/*.pdf, relative to data/raw/)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "cache" / "pdf_links.json"


def links(pdf: Path) -> list[str]:
    with pymupdf.open(pdf) as doc:
        uris = [link["uri"] for page in doc for link in page.get_links() if link.get("uri")]
    return list(dict.fromkeys(u.strip() for u in uris))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("globs", nargs="*", default=["parents/*.pdf"], help="globs relative to data/raw/")
    args = parser.parse_args()
    pdfs = sorted({p for g in args.globs for p in RAW.glob(g)})
    result = {p.relative_to(ROOT).as_posix(): links(p) for p in pdfs}
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    code = sum(any("github.com" in u or "gitlab.com" in u for u in v) for v in result.values())
    print(f"{len(result)} PDFs; {code} have a GitHub/GitLab link -> {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
