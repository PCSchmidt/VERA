"""Enumerate every generated paper the ScientistTwo site lists (Increment 0, task 2).

Source: the site publishes no data file. Its only listing is the `paperData`
object in index.html (one `{ label: "Sub-domain (Method)", file: "..." }` per
paper, grouped by domain key; domain names come from `categories`). This
script parses that object, cross-checks it against the PDFs in the site's
GitHub repo, and writes:

- data/corpus_discovery.json: source, stated vs discovered count, explanation,
  and the per-paper list (see data/README.md);
- data/corpus_inventory.csv: one seeded row per paper (id, domain, sub-domain,
  method). Existing rows are kept; the template row is dropped.

Polite by construction: two requests (three with robots.txt), spaced by
--delay seconds, with robots.txt honoured.

Usage: uv run python scripts/discover_corpus.py [--no-crosscheck] [--delay 2]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from pathlib import Path
from urllib.parse import quote

SITE = "https://scientist-two.github.io/"
REPO_TREE = "https://api.github.com/repos/scientist-two/scientist-two.github.io/git/trees/HEAD?recursive=1"
USER_AGENT = "VERA-corpus-discovery/0.1 (+https://github.com/PCSchmidt)"
ROOT = Path(__file__).resolve().parents[1]

INVENTORY_COLUMNS = [
    "gen_paper_id", "domain", "subdomain", "method_name", "gen_pdf_url", "gen_code_url",
    "parent_title", "parent_venue", "parent_id_arxiv_or_doi", "parent_code_url",
    "reported_gain_pct", "compute_class", "candidate_for_p3", "notes",
]  # fmt: skip
TEMPLATE_ID = "example-001"
Row = dict[str, str]

_CATEGORY = re.compile(r"\{\s*key:\s*'([^']+)',\s*name:\s*'([^']+)'\s*\}")
_DOMAIN_OPEN = re.compile(r"^\s*(\w+):\s*\[", re.MULTILINE)
_PAPER = re.compile(r'\{\s*label:\s*"([^"]+)",\s*file:\s*"([^"]+)"\s*\}')
_STATED = re.compile(r'id="total-count"[^>]*>\s*(\d+)\s*<')
_HEADLINE = re.compile(r"(\d+) of (\d+) research problems")


# ── parsing (pure; tested without network) ────────────────────────────────────


def _block(html: str, name: str, open_ch: str, close_ch: str) -> str:
    """Body of `const <name> = <open> ... <close>;`, found by bracket matching."""
    match = re.search(rf"const\s+{name}\s*=\s*\{open_ch}", html)
    if not match:
        raise ValueError(f"page has no `const {name}` listing; the site layout changed")
    depth, start = 0, match.end() - 1
    for i in range(start, len(html)):
        if html[i] == open_ch:
            depth += 1
        elif html[i] == close_ch:
            depth -= 1
            if depth == 0:
                return html[start + 1 : i]
    raise ValueError(f"unterminated `const {name}` in page")


def split_label(label: str) -> tuple[str, str]:
    """'Sub-domain (Method)' -> (sub-domain, method), as the page's subDomainOf/methodOf do."""
    i = label.rfind(" (")
    return (label, "") if i == -1 else (label[:i], label[i + 2 : -1])


def pdf_url(file: str) -> str:
    """Absolute URL, encoding each path segment like the page's pdfUrl()."""
    return SITE + "/".join(quote(seg, safe="") for seg in file.split("/"))


def parse_listing(html: str) -> list[dict[str, str]]:
    domains = dict(_CATEGORY.findall(_block(html, "categories", "[", "]")))
    body = _block(html, "paperData", "{", "}")
    starts = list(_DOMAIN_OPEN.finditer(body))
    papers = []
    for n, start in enumerate(starts):
        key = start.group(1)
        chunk = body[start.end() : starts[n + 1].start() if n + 1 < len(starts) else len(body)]
        for label, file in _PAPER.findall(chunk):
            subdomain, method = split_label(label)
            papers.append(
                {
                    "gen_paper_id": f"{key}/{Path(file).stem}",
                    "domain": domains.get(key, key),
                    "subdomain": subdomain,
                    "method_name": method,
                    "file": file,
                    "pdf_url": pdf_url(file),
                }
            )
    return papers


def parse_stated_count(html: str) -> int | None:
    match = _STATED.search(html)
    return int(match.group(1)) if match else None


def explain(html: str, stated: int | None, papers: list[dict[str, str]], repo_pdfs: list[str] | None) -> str:
    lines = []
    if stated is None:
        lines.append("The gallery states no total.")
    elif stated != len(papers):
        lines.append(f"The gallery states {stated} papers but its listing has {len(papers)}.")
    else:
        lines.append(f"The gallery's stated total ({stated}) matches its listing.")
    headline = _HEADLINE.search(html)
    if headline:
        lines.append(
            f"Separately, the site headline reports beating human SOTA on {headline[1]} of {headline[2]} "
            "research problems; that counts problems, not listed papers, so it is not the corpus size."
        )
    if repo_pdfs is not None:
        listed = {p["file"] for p in papers}
        on_disk = set(repo_pdfs)
        if listed == on_disk:
            lines.append(f"Cross-check: the site's GitHub repo holds exactly these {len(on_disk)} PDFs.")
        else:
            lines.append(
                f"Cross-check: repo has {len(on_disk)} PDFs; not listed: {sorted(on_disk - listed)}; "
                f"listed but missing from repo: {sorted(listed - on_disk)}."
            )
    return " ".join(lines)


def seed_inventory(existing: list[Row], papers: list[Row]) -> tuple[list[Row], list[str]]:
    """Keep existing rows, drop the template, add one row per new paper. Returns (rows, stale ids)."""
    rows = [r for r in existing if r.get("gen_paper_id") != TEMPLATE_ID]
    have = {r["gen_paper_id"] for r in rows}
    for p in papers:
        if p["gen_paper_id"] not in have:
            row = dict.fromkeys(INVENTORY_COLUMNS, "")
            row.update({k: p[k] for k in ("gen_paper_id", "domain", "subdomain", "method_name")})
            rows.append(row)
    listed = {p["gen_paper_id"] for p in papers}
    return rows, sorted(have - listed)


# ── network ───────────────────────────────────────────────────────────────────


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def robots_allows(url: str) -> bool:
    robots = urllib.robotparser.RobotFileParser(SITE + "robots.txt")
    try:
        robots.parse(fetch(SITE + "robots.txt").splitlines())
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            return False
        return True  # 404 etc.: no robots.txt, nothing disallowed
    return robots.can_fetch(USER_AGENT, url)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between requests")
    parser.add_argument("--no-crosscheck", action="store_true", help="skip the GitHub repo cross-check")
    args = parser.parse_args()

    if not robots_allows(SITE):
        sys.exit(f"robots.txt disallows {SITE}")
    time.sleep(args.delay)
    html = fetch(SITE)
    papers = parse_listing(html)
    if not papers:
        sys.exit("no papers parsed from the page listing")
    stated = parse_stated_count(html)

    repo_pdfs = None
    if not args.no_crosscheck:
        time.sleep(args.delay)
        tree = json.loads(fetch(REPO_TREE))
        paths = [t["path"] for t in tree.get("tree", [])]
        repo_pdfs = [x for x in paths if x.startswith("generated-papers/") and x.endswith(".pdf")]

    record = {
        "source_url": SITE + "index.html#gallery (const paperData)",
        "retrieved": dt.date.today().isoformat(),
        "site_stated_count": stated,
        "discovered_count": len(papers),
        "explanation": explain(html, stated, papers, repo_pdfs),
        "crosscheck_url": None if repo_pdfs is None else REPO_TREE,
        "papers": papers,
    }
    out = ROOT / "data" / "corpus_discovery.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    inv_path = ROOT / "data" / "corpus_inventory.csv"
    existing = []
    if inv_path.exists():
        with inv_path.open(encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))
    rows, stale = seed_inventory(existing, papers)
    with inv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"discovered {len(papers)} papers (site states {stated}); wrote {out.relative_to(ROOT)}")
    print(f"inventory: {len(rows)} rows in {inv_path.relative_to(ROOT)}")
    if stale:
        print(f"WARNING: inventory rows no longer on the site: {stale}", file=sys.stderr)


if __name__ == "__main__":
    main()
