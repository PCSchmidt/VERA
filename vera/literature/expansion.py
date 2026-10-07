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
import re
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


MAX_REFS_PER_SEED = 60  # reference-list entries resolved per seed on the GROBID route (each costs one lookup)
YEAR_SLACK = 1


def _year_gap(a: object, b: object) -> int | None:
    """The distance in years between two year strings, or None when either has no four-digit year in it."""
    ya, yb = re.search(r"\d{4}", str(a or "")), re.search(r"\d{4}", str(b or ""))
    return abs(int(ya.group()) - int(yb.group())) if ya and yb else None


def resolve(retriever: Retriever, ref: dict) -> dict | None:
    """The OpenAlex record for one parsed reference (by DOI, else by title and year); None when it is not found."""
    key = retrieval.api_key("OPENALEX_API_KEY")
    select = retrieval.OPENALEX_FIELDS
    try:
        if ref.get("doi"):
            work = json.loads(retriever._request("openalex", f"{OPENALEX}/doi:{ref['doi']}",  # noqa: SLF001
                                                 {"select": select, "api_key": key}))
            found = _openalex_records(json.dumps({"results": [work]}), "cited by seeds")
        else:
            text = retriever._request("openalex", OPENALEX, {"search": ref["title"], "per-page": 3,  # noqa: SLF001
                                                              "select": select, "api_key": key})  # fmt: skip
            found = _openalex_records(text, "cited by seeds")
    except Exception:  # noqa: BLE001 - one reference that cannot be looked up is skipped
        return None
    for rec in found:
        gap = _year_gap(ref.get("year"), rec.get("year"))
        # an unreadable year (a parser fragment like "Apri") does not rule a match out
        year_ok = gap is None or gap <= YEAR_SLACK
        if year_ok and retrieval.title_similarity(ref["title"], rec["title"]) >= retrieval.TITLE_MATCH:
            return rec
    return None


def expand(
    retriever: Retriever, records: list[dict], seeds: list[dict], today: str | None = None, references_of=None
) -> list[dict]:
    """New candidate records (not already in `records`), cited by the seeds, with keys that continue `records`'.

    A seed's references come from OpenAlex when it lists them; for a paper OpenAlex has not processed yet (recent
    arXiv preprints) `references_of(seed)` supplies the parsed reference list of its PDF (GROBID, T3) and each entry
    is resolved to an OpenAlex record. Candidates are ranked by how many seeds cite them, then by the order the seeds
    were given; each carries `cited_by` (the seeds' keys) as its provenance, `query` "cited by R5, R9" and a rank."""
    cand: dict[str, dict] = {}
    who: dict[str, list[str]] = {}
    counts: Counter = Counter()
    needs_pdf: list[dict] = []
    for seed in seeds[:MAX_SEEDS]:
        refs = (seed_work(retriever, seed) or {}).get("referenced_works", [])
        for ref in refs:
            counts[ref] += 1
            who.setdefault(ref, []).append(seed["key"])
        if not refs:
            needs_pdf.append(seed)
    if counts:
        order = [w for w, _ in counts.most_common()][: MAX_ADDED * 2]
        for rec in fetch_works(retriever, order):
            cand[rec["openalex_id"]] = rec
    for seed in needs_pdf if references_of else []:
        for ref in references_of(seed)[:MAX_REFS_PER_SEED]:
            rec = resolve(retriever, ref)
            if rec and rec.get("openalex_id"):
                cand.setdefault(rec["openalex_id"], rec)
                if seed["key"] not in who.setdefault(rec["openalex_id"], []):
                    who[rec["openalex_id"]].append(seed["key"])
    ranked = sorted(cand.values(), key=lambda r: -len(who.get(r["openalex_id"], [])))  # stable: seed order on ties
    fresh: list[dict] = []
    for rec in ranked:
        if any(same_paper(rec, old) for old in records) or any(same_paper(rec, new) for new in fresh):
            continue
        citing = who.get(rec["openalex_id"], [])
        fresh.append({**rec, "cited_by": citing, "query": "cited by " + ", ".join(citing), "rank": len(fresh) + 1,
                      "hits": len(citing), "n_queries": len(citing)})  # fmt: skip
    day = today or dt.date.today().isoformat()
    return [{**r, "key": f"R{len(records) + i}", "retrieved": day} for i, r in enumerate(fresh[:MAX_ADDED], start=1)]
