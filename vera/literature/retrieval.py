"""Retrieval (T5 as decided: Crossref and arXiv keyless; OpenAlex, Semantic Scholar only with the user's own keys).

`Retriever` runs a query against the available sources and returns candidate records (title, authors, year, id, url,
abstract, open-access PDF link, source). Requests carry a User-Agent naming the project and no email, are paced (arXiv
asks for one request per three seconds) and are cached by URL and parameters with their retrieval date, so a rerun
never queries twice. A source that fails is skipped; if every source fails, `LookupUnavailable` is raised.

`merge_records` deduplicates across queries and sources (arXiv id, DOI, then near-identical titles) and ranks the result
by the best rank any query gave a record. `recall` measures how many of a topic's key papers a retrieved set contains,
before and after the relevance screen and within the top N by rank (T5 reverse-if (1)); it never feeds back into the
retrieval (the key papers are fixed before the first retrieval, SPEC "No peeking").
"""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

import httpx

from vera.audit.bibliography import ATOM, PAUSE, USER_AGENT, LookupUnavailable, normalise
from vera.backends import api_key

# v1 returned figure and table captions and dataset components from Crossref; v2 asks for papers only
OPENALEX_FIELDS = "id,doi,title,publication_year,authorships,abstract_inverted_index,best_oa_location"
S2_FIELDS = "title,year,authors,abstract,externalIds,openAccessPdf,venue"
PAPER_TYPES = ("journal-article", "proceedings-article", "posted-content", "book-chapter", "report")
CROSSREF_TYPES = ",".join(f"type:{t}" for t in PAPER_TYPES)
TITLE_MATCH = 0.90  # normalised-title similarity that counts as a key paper being found (the T5 rule)
DEDUPE_MATCH = 0.97  # stricter for merging two search hits: "Part I" and "Part II" are different papers
USER_AGENT_LIT = USER_AGENT.replace("citation existence checks", "literature retrieval")


class HttpCache:
    """GET responses stored under `directory` by URL and parameters, with the date they were retrieved."""

    def __init__(self, directory: Path | None) -> None:
        self.directory = directory

    def key(self, url: str, params: dict) -> str:
        return hashlib.sha1(json.dumps([url, sorted(params.items())], default=str).encode()).hexdigest()[:20]

    def get(self, url: str, params: dict) -> dict | None:
        if self.directory is None:
            return None
        path = self.directory / f"{self.key(url, params)}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def put(self, url: str, params: dict, text: str) -> None:
        if self.directory is None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        entry = {"url": url, "params": {k: v for k, v in params.items() if k != "api_key"},
                 "retrieved": dt.date.today().isoformat(), "text": text}  # fmt: skip
        (self.directory / f"{self.key(url, params)}.json").write_text(json.dumps(entry), encoding="utf-8")


def _strip_tags(text: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", text or "").split())


def _arxiv_records(text: str, query: str) -> list[dict]:
    out = []
    for rank, e in enumerate(ET.fromstring(text).findall("a:entry", ATOM), start=1):
        url = (e.findtext("a:id", "", ATOM) or "").strip()
        arxiv_id = url.rsplit("/abs/", 1)[-1].split("v")[0]
        out.append({
            "title": " ".join((e.findtext("a:title", "", ATOM) or "").split()),
            "authors": [" ".join((a.findtext("a:name", "", ATOM) or "").split()) for a in e.findall("a:author", ATOM)],
            "year": (e.findtext("a:published", "", ATOM) or "")[:4],
            "id": f"arXiv:{arxiv_id}", "url": f"https://arxiv.org/abs/{arxiv_id}",
            "abstract": " ".join((e.findtext("a:summary", "", ATOM) or "").split()),
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}", "source": "arxiv", "query": query, "rank": rank,
        })  # fmt: skip
    return out


def _crossref_records(text: str, query: str) -> list[dict]:
    out = []
    for rank, it in enumerate(json.loads(text)["message"]["items"], start=1):
        parts = (it.get("issued") or {}).get("date-parts") or [[None]]
        doi = it.get("DOI", "")
        out.append({
            "title": " ".join(((it.get("title") or [""])[0]).split()), "year": str(parts[0][0] or ""),
            "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])],
            "id": f"doi:{doi}" if doi else "", "url": f"https://doi.org/{doi}" if doi else "",
            "venue": (it.get("container-title") or [None])[0], "abstract": _strip_tags(it.get("abstract", "")) or None,
            "pdf_url": None, "source": "crossref", "query": query, "rank": rank,
        })  # fmt: skip
    return out


def _openalex_records(text: str, query: str) -> list[dict]:
    out = []
    for rank, w in enumerate(json.loads(text)["results"], start=1):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        index = w.get("abstract_inverted_index") or {}
        words = sorted(((pos, word) for word, poss in index.items() for pos in poss))
        out.append({
            "title": w.get("title") or "", "year": str(w.get("publication_year") or ""),
            "authors": [(a.get("author") or {}).get("display_name", "") for a in w.get("authorships", [])],
            "id": f"doi:{doi}" if doi else (w.get("id") or ""), "url": w.get("doi") or w.get("id") or "",
            "abstract": " ".join(word for _, word in words) or None,
            "pdf_url": (w.get("best_oa_location") or {}).get("pdf_url"), "source": "openalex",
            "query": query, "rank": rank, "openalex_id": w.get("id"),
        })  # fmt: skip
    return out


def _s2_records(text: str, query: str) -> list[dict]:
    out = []
    for rank, p in enumerate(json.loads(text).get("data") or [], start=1):
        ext = p.get("externalIds") or {}
        if ext.get("ArXiv"):
            pid, url = f"arXiv:{ext['ArXiv']}", f"https://arxiv.org/abs/{ext['ArXiv']}"
        elif ext.get("DOI"):
            pid, url = f"doi:{ext['DOI']}", f"https://doi.org/{ext['DOI']}"
        else:
            pid, url = f"s2:{p.get('paperId', '')}", f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}"
        out.append({
            "title": " ".join((p.get("title") or "").split()), "year": str(p.get("year") or ""),
            "authors": [a.get("name", "") for a in p.get("authors") or []], "id": pid, "url": url,
            "venue": p.get("venue") or None, "abstract": p.get("abstract") or None,
            "pdf_url": (p.get("openAccessPdf") or {}).get("url"), "source": "semanticscholar",
            "query": query, "rank": rank,
        })  # fmt: skip
    return out


class Retriever:
    """Callable: query -> candidate records from every available source (Crossref and arXiv; OpenAlex and Semantic
    Scholar with the user's own keys)."""

    def __init__(self, client: httpx.Client | None = None, *, cache: HttpCache | None = None, per_query: int = 10,
                 pace: bool = True, now: Callable[[], float] = time.monotonic,
                 sources: list[str] | None = None) -> None:  # fmt: skip
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT_LIT})
        self.cache, self.per_query, self.pace = cache or HttpCache(None), per_query, pace
        self.sources = list(sources) if sources is not None else ["crossref", "arxiv"]
        if sources is None:  # OpenAlex and Semantic Scholar only with the user's own key (T5); OpenAlex is primary (v2)
            try:
                api_key("OPENALEX_API_KEY")
                self.sources.insert(0, "openalex")
            except KeyError:
                pass
            try:
                api_key("SEMANTIC_SCHOLAR_API_KEY")
                self.sources.append("semanticscholar")  # last: a second keyed source adds to, never reorders, the first
            except KeyError:
                pass
        self._last: dict[str, float] = {}
        self._now = now

    def _request(self, source: str, url: str, params: dict, headers: dict | None = None) -> str:
        cached = self.cache.get(url, params)
        if cached is not None:
            return cached["text"]
        for attempt in range(4):
            if self.pace:
                wait = PAUSE[source] - (self._now() - self._last.get(source, -1e9))
                if wait > 0:
                    time.sleep(wait)
            self._last[source] = self._now()
            try:
                resp = self.client.get(url, params=params, headers=headers)
            except httpx.TransportError:
                if attempt == 3:
                    raise
            else:
                if resp.status_code not in {429, 500, 502, 503, 504} or attempt == 3:
                    resp.raise_for_status()
                    self.cache.put(url, params, resp.text)
                    return resp.text
            time.sleep(3 * (attempt + 1) if self.pace else 0)
        raise AssertionError("unreachable")

    def __call__(self, query: str) -> list[dict]:
        found: list[dict] = []
        errors = []
        n = self.per_query
        for source in self.sources:
            try:
                if source == "arxiv":
                    text = self._request(source, "https://export.arxiv.org/api/query",
                                         {"search_query": f"all:{query}", "max_results": n})  # fmt: skip
                    found += _arxiv_records(text, query)
                elif source == "crossref":
                    text = self._request(source, "https://api.crossref.org/works",
                                         {"query": query, "rows": n, "filter": CROSSREF_TYPES,
                                          "select": "title,issued,DOI,author,container-title,abstract"})  # fmt: skip
                    found += _crossref_records(text, query)
                elif source == "semanticscholar":
                    text = self._request(source, "https://api.semanticscholar.org/graph/v1/paper/search",
                                         {"query": query, "limit": n, "fields": S2_FIELDS},
                                         {"x-api-key": api_key("SEMANTIC_SCHOLAR_API_KEY")})  # fmt: skip
                    found += _s2_records(text, query)
                else:
                    params = {"search": query, "per-page": n, "api_key": api_key("OPENALEX_API_KEY"),
                              "filter": "type:article|preprint",
                              "select": OPENALEX_FIELDS}
                    text = self._request(source, "https://api.openalex.org/works", params)
                    found += _openalex_records(text, query)
            except (httpx.HTTPError, ET.ParseError, KeyError, ValueError) as exc:
                errors.append(f"{source}: {type(exc).__name__}")
        if errors and len(errors) == len(self.sources):
            raise LookupUnavailable("; ".join(errors))
        return [r for r in found if r["title"]]


# ── merging and ranking ──────────────────────────────────────────────────────────────────────────────


def title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalise(a), normalise(b)).ratio()


ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def same_paper(a: dict, b: dict) -> bool:
    if a.get("id") and a["id"] == b.get("id"):
        return True
    if title_similarity(a["title"], b["title"]) < DEDUPE_MATCH:
        return False
    differing = set(normalise(a["title"]).split()) ^ set(normalise(b["title"]).split())
    return not any(t.isdigit() or t in ROMAN for t in differing)  # "part I" and "part 2" are different papers


def merge_records(hits: list[dict], today: str | None = None) -> list[dict]:
    """Deduplicate `hits` (records from any query or source) and rank them. Each result keeps the best rank any query
    gave it, how many queries found it, the query that gave the best rank, and an abstract or PDF link from any source
    that had one. Keys R1, R2, ... follow the ranking (best rank first, then most queries)."""
    merged: list[dict] = []
    for hit in hits:
        for m in merged:
            if same_paper(m, hit):
                m["hits"] += 1
                m["queries"].add(hit["query"])
                if hit["rank"] < m["rank"]:
                    m.update(rank=hit["rank"], query=hit["query"])
                for field in ("abstract", "pdf_url", "venue"):
                    m[field] = m.get(field) or hit.get(field)
                if hit["id"].startswith("arXiv:") and not m["id"].startswith("arXiv:"):
                    m.update(id=hit["id"], url=hit["url"], source="arxiv")  # prefer the preprint record's id
                break
        else:
            merged.append({**hit, "hits": 1, "queries": {hit["query"]}})
    merged.sort(key=lambda m: (m["rank"], -len(m["queries"]), m["title"]))
    day = today or dt.date.today().isoformat()
    out = []
    for i, m in enumerate(merged, start=1):
        rest = {k: v for k, v in m.items() if k != "queries"}
        out.append({**rest, "key": f"R{i}", "retrieved": day, "n_queries": len(m["queries"])})
    return out


# ── recall of the key papers ─────────────────────────────────────────────────────────────────────────


def matches(key_paper: dict, record: dict) -> bool:
    """A retrieved record is the key paper when the identifiers agree, or the normalised titles are near-identical."""
    kid = key_paper.get("id", "").lower()
    rid = (record.get("id") or "").lower()
    if kid and rid and kid == rid:
        return True
    return title_similarity(key_paper["title"], record["title"]) >= TITLE_MATCH


def recall(key_papers: list[dict], records: list[dict], kept: set[str], top_n: int = 30) -> dict:
    """Per key paper: the matching record (or None) before the screen, after it, and within the top `top_n` by rank.

    `records` are ranked (merge_records order); `kept` is the set of keys that passed the relevance screen."""
    rows = []
    for kp in key_papers:
        hit = next((r for r in records if matches(kp, r)), None)
        position = records.index(hit) + 1 if hit else None
        rows.append({"title": kp["title"], "id": kp.get("id"), "found": hit is not None,
                     "key": hit["key"] if hit else None, "kept": bool(hit and hit["key"] in kept),
                     "in_top": bool(position and position <= top_n), "position": position})  # fmt: skip
    n = len(rows)
    return {"n_key_papers": n, "found": sum(r["found"] for r in rows) / n, "kept": sum(r["kept"] for r in rows) / n,
            "in_top": sum(r["in_top"] for r in rows) / n, "top_n": top_n, "rows": rows}  # fmt: skip
