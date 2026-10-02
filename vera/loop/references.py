"""References the loop is allowed to cite: records it actually retrieved, not titles a model remembers.

The write-up cites `[R1]`, `[R2]`, ... and its reference list is built from these records, never from model text.
Retrieval goes to arXiv by id (T5: Crossref and arXiv are the keyless pair); each record is appended to
`retrieved.jsonl` in the run directory, which is the retrieval log the final audit matches citations against
before it looks anything up (SPEC, "Minimal P1").
"""

from __future__ import annotations

import datetime as dt
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ARXIV = "https://export.arxiv.org/api/query"
USER_AGENT = "VERA-research/0.1 (+https://github.com/PCSchmidt/VERA; reference retrieval)"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
SEED_ARXIV_IDS = {"2510.24815": "the parent method (TreeHFD)", "1603.02754": "the xgboost model"}


def fetch_arxiv(ids: list[str], client: httpx.Client | None = None) -> list[dict]:
    """Bibliographic records for arXiv ids, as retrieved (title, authors, year, id, url)."""
    own = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
    try:
        for attempt in range(4):  # intermittent DNS failures, and arXiv asks for patience
            try:
                resp = client.get(ARXIV, params={"id_list": ",".join(ids), "max_results": len(ids)})
                resp.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 3:
                    raise
                time.sleep(3 * (attempt + 1))
    finally:
        if own:
            client.close()
    records = []
    for entry in ET.fromstring(resp.text).findall("a:entry", ATOM):
        url = entry.findtext("a:id", "", ATOM).strip()
        arxiv_id = url.rsplit("/abs/", 1)[-1].split("v")[0]
        records.append({
            "title": " ".join((entry.findtext("a:title", "", ATOM) or "").split()),
            "authors": [" ".join((a.findtext("a:name", "", ATOM) or "").split())
                        for a in entry.findall("a:author", ATOM)],
            "year": (entry.findtext("a:published", "", ATOM) or "")[:4],
            "id": f"arXiv:{arxiv_id}",
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "source": "arxiv",
        })  # fmt: skip
    return records


def retrieve_seed_references(run_dir: Path, fetch=fetch_arxiv) -> list[dict]:
    """Retrieve the seed references once per run and log them; later calls return the logged records."""
    log = run_dir / "retrieved.jsonl"
    if log.exists():
        return load_references(run_dir)
    records = fetch(list(SEED_ARXIV_IDS))
    if not records:
        raise RuntimeError("arXiv returned no records for the seed references")
    stamp = dt.date.today().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(records, 1):
            fh.write(json.dumps({"key": f"R{i}", "retrieved": stamp, **rec}, ensure_ascii=False) + "\n")
    return load_references(run_dir)


def load_references(run_dir: Path) -> list[dict]:
    log = run_dir / "retrieved.jsonl"
    return [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]


def format_reference(rec: dict) -> str:
    authors = rec["authors"]
    who = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    return f"[{rec['key']}] {who}. {rec['title']}. {rec['year']}. {rec['id']}. {rec['url']}"
