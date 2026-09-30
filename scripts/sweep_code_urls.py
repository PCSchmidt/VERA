"""Cross-check every inventory row's parent_code_url against the parent PDFs (Increment 0).

For each row, collects repository URLs (GitHub, GitLab, Bitbucket, Hugging
Face) from every PDF held for its parent: the version the inventory was built
from and, where one exists, the camera-ready (data/parent_versions.csv).
URLs are taken from the extracted text, with URLs broken across lines
rejoined, and from the PDFs' link annotations (data/cache/pdf_links.json).

Reports rows where parent_code_url is `unknown` but a candidate exists, and
rows whose recorded URL appears in none of the parent's PDFs. A candidate is
not automatically the parent's own code (papers link third-party repos too),
so the report is for review, not an automatic fix.

Usage: uv run python scripts/sweep_code_urls.py
       (run scripts/extract_text.py and scripts/pdf_links.py on the parents first)
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = r"(?:github\.com|gitlab\.com|bitbucket\.org|huggingface\.co)"


def norm(url: str) -> str:
    url = url.split("#")[0].split("?")[0]
    return re.sub(r"(\.git)?[/.,;:)\]]*$", "", url).lower()


def candidates(pdf_rel: str, links: dict[str, list[str]]) -> set[str]:
    text_file = ROOT / "data" / "cache" / "text" / Path(pdf_rel).relative_to("data/raw").with_suffix(".txt")
    text = text_file.read_text(encoding="utf-8") if text_file.exists() else ""
    text = re.sub(r"(https?://\S*?[/\-_.])\s*\n\s*(?=[A-Za-z0-9])", r"\1", text)  # rejoin split URLs
    urls = set(re.findall(rf"https?://{HOST}/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", text))
    urls |= {u for u in links.get(pdf_rel, []) if re.search(HOST, u)}
    return {norm(u) for u in urls if u.count("/") >= 4}


def main() -> None:
    links = json.loads((ROOT / "data" / "cache" / "pdf_links.json").read_text(encoding="utf-8"))
    with (ROOT / "data" / "parent_papers.csv").open(encoding="utf-8", newline="") as f:
        parents = {r["parent_title"]: r for r in csv.DictReader(f)}
    versions = {}
    path = ROOT / "data" / "parent_versions.csv"
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            versions = {r["parent_title"]: r for r in csv.DictReader(f)}
    with (ROOT / "data" / "corpus_inventory.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    unknown_found, unsupported = 0, 0
    for r in rows:
        pdfs = [parents[r["parent_title"]]["pdf_path"], versions.get(r["parent_title"], {}).get("camera_ready_pdf", "")]
        found = set().union(*(candidates(p, links) for p in pdfs if p))
        rec = r["parent_code_url"]
        if rec == "unknown" and found:
            unknown_found += 1
            print(f"UNKNOWN BUT FOUND | {r['gen_paper_id']} | {sorted(found)}")
        elif rec.startswith("http") and not any(norm(rec).startswith(u) or u.startswith(norm(rec)) for u in found):
            unsupported += 1
            print(f"NOT IN ANY PDF    | {r['gen_paper_id']} | {rec} | {sorted(found)[:4]}")
    print(f"{len(rows)} rows: {unknown_found} unknown with candidates, {unsupported} recorded URLs not in the PDFs")


if __name__ == "__main__":
    main()
