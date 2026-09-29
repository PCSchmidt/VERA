"""Download the generated-paper PDFs with provenance (Increment 0, task 3; FND-C-02).

Reads the paper list from data/corpus_discovery.json (scripts/discover_corpus.py),
downloads each PDF to data/raw/scientisttwo/<domain key>/<file name>, records
{path, url, retrieved, sha256} in data/provenance.jsonl, and fills
`gen_pdf_url` in data/corpus_inventory.csv (`unknown` when the site returns 404).

Polite and resumable: robots.txt honoured, --delay seconds between downloads,
and files whose hash already matches their record are skipped without a request.
A download lands in a .part file and is only moved into place after it checks
out as a PDF, so an interrupted run never leaves an unrecorded file behind.

Usage: uv run python scripts/fetch_corpus.py [--delay 2] [--limit N]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from discover_corpus import INVENTORY_COLUMNS, SITE, USER_AGENT, robots_allows

from vera import provenance

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "scientisttwo"
PREFIX = "generated-papers/"


def local_path(file: str) -> Path:
    """Site path 'generated-papers/<domain>/<name>.pdf' -> data/raw/scientisttwo/<domain>/<name>.pdf."""
    if not file.startswith(PREFIX) or ".." in file.split("/"):
        raise ValueError(f"unexpected site path: {file!r}")
    return RAW.joinpath(*file[len(PREFIX) :].split("/"))


def download(url: str, dest: Path) -> None:
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, part.open("wb") as out:
            while chunk := resp.read(1 << 16):
                out.write(chunk)
        with part.open("rb") as fh:
            if fh.read(5) != b"%PDF-":
                raise ValueError(f"{url} did not return a PDF")
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)


def update_inventory(urls: dict[str, str]) -> None:
    path = ROOT / "data" / "corpus_inventory.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["gen_paper_id"] in urls:
            row["gen_pdf_url"] = urls[row["gen_paper_id"]]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between downloads")
    parser.add_argument("--limit", type=int, default=None, help="download at most N new files (for a trial run)")
    args = parser.parse_args()

    discovery = json.loads((ROOT / "data" / "corpus_discovery.json").read_text(encoding="utf-8"))
    papers = discovery["papers"]
    if not robots_allows(SITE):
        sys.exit(f"robots.txt disallows {SITE}")

    records = provenance.load(ROOT)
    urls: dict[str, str] = {}
    fetched = skipped = 0
    failed: list[str] = []
    for paper in papers:
        dest = local_path(paper["file"])
        if provenance.is_current(ROOT, dest, records):
            urls[paper["gen_paper_id"]] = paper["pdf_url"]
            skipped += 1
            continue
        if args.limit is not None and fetched >= args.limit:
            continue
        time.sleep(args.delay)
        try:
            download(paper["pdf_url"], dest)
        except urllib.error.HTTPError as err:
            failed.append(f"{paper['gen_paper_id']}: HTTP {err.code}")
            if err.code == 404:
                urls[paper["gen_paper_id"]] = "unknown"
            continue
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            failed.append(f"{paper['gen_paper_id']}: {err}")
            continue
        provenance.record(ROOT, dest, paper["pdf_url"])
        urls[paper["gen_paper_id"]] = paper["pdf_url"]
        fetched += 1
        print(f"[{fetched}] {dest.relative_to(ROOT).as_posix()}", flush=True)

    update_inventory(urls)
    print(f"fetched {fetched}, already current {skipped}, failed {len(failed)}, of {len(papers)} listed")
    for line in failed:
        print(f"FAILED {line}", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
