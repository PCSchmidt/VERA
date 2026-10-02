"""Snowballing: from the papers the relevance screen kept, follow their reference lists (OpenAlex `referenced_works`).

Keyword search finds papers whose words match the queries; a literature review also reads what the central papers cite.
Retrieval v1 and v2 (keyword search through Crossref, arXiv and OpenAlex) found few of a topic's key papers and only
a handful of relevant candidates, so the stage now expands from its seeds: the works cited by several seeds are
candidates, ranked by how many seeds cite them. This is an addition made after the first retrieval measurement (the
Increment 3 review reports it as such); it needs the user's own OpenAlex key (T5: never a maintainer key), and without
one the stage skips it and says so.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter

from vera.literature import retrieval
from vera.literature.retrieval import Retriever, _openalex_records, same_paper

OPENALEX = "https://api.openalex.org/works"
BATCH = 40  # works per metadata request
MAX_SEEDS = 5
MAX_ADDED = 40


def short_id(openalex_url: str) -> str:
    return openalex_url.rsplit("/", 1)[-1]


def seed_work(retriever: Retriever, record: dict) -> dict | None:
    """The seed's OpenAlex work (id and referenced works), found by DOI or arXiv DOI; None when OpenAlex lacks it."""
    ident = record.get("id", "")
    if ident.startswith("arXiv:"):
        doi = f"10.48550/arXiv.{ident.split(':', 1)[1]}"
    elif ident.startswith("doi:"):
        doi = ident.split(":", 1)[1]
    elif record.get("openalex_id"):
        doi = None
    else:
        return None
    key = retrieval.api_key("OPENALEX_API_KEY")
    params = {"select": "id,doi,referenced_works", "api_key": key}
    url = f"{OPENALEX}/{record['openalex_id']}" if record.get("openalex_id") else f"{OPENALEX}/doi:{doi}"
    try:
        return json.loads(retriever._request("openalex", url, params))  # noqa: SLF001 - same pacing and cache
    except Exception:  # noqa: BLE001 - a seed OpenAlex does not know is skipped, not fatal
        return None


def cited_by_seeds(retriever: Retriever, seeds: list[dict]) -> tuple[Counter, dict[str, list[str]]]:
    """How many seeds cite each work, and which (by record key)."""
    counts: Counter = Counter()
    who: dict[str, list[str]] = {}
    for seed in seeds[:MAX_SEEDS]:
        work = seed_work(retriever, seed)
        for ref in (work or {}).get("referenced_works", []):
            counts[ref] += 1
            who.setdefault(ref, []).append(seed["key"])
    return counts, who


def fetch_works(retriever: Retriever, ids: list[str]) -> list[dict]:
    """Records for OpenAlex work ids (batched), in the retriever's record shape."""
    out: list[dict] = []
    key = retrieval.api_key("OPENALEX_API_KEY")
    for i in range(0, len(ids), BATCH):
        batch = [short_id(w) for w in ids[i : i + BATCH]]
        params = {"filter": "openalex:" + "|".join(batch), "per-page": BATCH, "api_key": key,
                  "select": retrieval.OPENALEX_FIELDS}  # fmt: skip
        text = retriever._request("openalex", OPENALEX, params)  # noqa: SLF001
        out += _openalex_records(text, "cited by seeds")
    return [r for r in out if r["title"]]


def expand(retriever: Retriever, records: list[dict], seeds: list[dict], today: str | None = None) -> list[dict]:
    """New candidate records (not already in `records`), cited by the seeds, with keys that continue `records`'.

    Ranked by how many seeds cite them, then by the order the seeds were given; each carries `cited_by` (the seeds'
    keys) as its provenance, `query` "cited by R5, R9" and a rank by position."""
    counts, who = cited_by_seeds(retriever, seeds)
    if not counts:
        return []
    order = [w for w, _ in counts.most_common()]  # most seeds first; ties keep the order the seeds listed them
    position = {w: i for i, w in enumerate(order)}
    works = fetch_works(retriever, order[: MAX_ADDED * 2])
    works.sort(key=lambda r: position.get(r.get("openalex_id") or "", 10**6))
    fresh: list[dict] = []
    for rec in works:
        if any(same_paper(rec, old) for old in records) or any(same_paper(rec, new) for new in fresh):
            continue
        citing = who.get(rec.get("openalex_id") or "", [])
        fresh.append({**rec, "cited_by": citing, "query": "cited by " + ", ".join(citing), "rank": len(fresh) + 1,
                      "hits": len(citing), "n_queries": len(citing)})  # fmt: skip
    day = today or dt.date.today().isoformat()
    return [{**r, "key": f"R{len(records) + i}", "retrieved": day} for i, r in enumerate(fresh[:MAX_ADDED], start=1)]
