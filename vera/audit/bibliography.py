"""Bibliographic lookup for the citation check (trade T5, decided 2026-10-01: Crossref and arXiv, keyless).

`SourceLookup` queries Crossref and the arXiv API by title and returns the top candidates as records
(`title`, `authors`, `year`, `id`, `url`, `source`); OpenAlex is added when `OPENALEX_API_KEY` is set (T5: it needs a
key, which is the user's own, never a maintainer key in an artifact). Requests carry a User-Agent naming the project
and no email, and are paced (arXiv asks for one request per three seconds). A source that fails is skipped; if every
source fails, `LookupUnavailable` is raised, so "could not look it up" is never mistaken for "not found".
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

import httpx

from vera.backends import api_key

USER_AGENT = "VERA-research/0.1 (+https://github.com/PCSchmidt/VERA; citation existence checks)"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
PAUSE = {"crossref": 0.3, "arxiv": 3.1, "openalex": 0.2, "semanticscholar": 1.1}
TOP = 3


class LookupUnavailable(RuntimeError):
    """Every bibliographic source failed: the reference could not be checked, which is not the same as not found."""


def normalise(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def _get(client: httpx.Client, url: str, params: dict, tries: int = 3) -> httpx.Response:
    for attempt in range(tries):
        try:
            resp = client.get(url, params=params)
        except httpx.TransportError:
            if attempt == tries - 1:
                raise
        else:
            if resp.status_code not in {429, 500, 502, 503, 504} or attempt == tries - 1:
                resp.raise_for_status()
                return resp
        time.sleep(3 * (attempt + 1))
    raise AssertionError("unreachable")


def _crossref(client: httpx.Client, title: str) -> list[dict]:
    resp = _get(
        client,
        "https://api.crossref.org/works",
        {"query.bibliographic": title, "rows": TOP, "select": "title,issued,DOI,author"},
    )
    out = []
    for it in resp.json()["message"]["items"]:
        parts = (it.get("issued") or {}).get("date-parts") or [[None]]
        out.append(
            {
                "title": (it.get("title") or [""])[0],
                "year": str(parts[0][0] or ""),
                "id": it.get("DOI", ""),
                "url": f"https://doi.org/{it['DOI']}" if it.get("DOI") else "",
                "source": "crossref",
                "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])],
            }
        )
    return out


def _arxiv(client: httpx.Client, title: str) -> list[dict]:
    words = " ".join(normalise(title).split()[:14])
    resp = _get(client, "https://export.arxiv.org/api/query", {"search_query": f'ti:"{words}"', "max_results": TOP})
    out = []
    for e in ET.fromstring(resp.text).findall("a:entry", ATOM):
        url = (e.findtext("a:id", "", ATOM) or "").strip()
        out.append(
            {
                "title": " ".join((e.findtext("a:title", "", ATOM) or "").split()),
                "year": (e.findtext("a:published", "", ATOM) or "")[:4],
                "id": "arXiv:" + url.rsplit("/abs/", 1)[-1].split("v")[0],
                "url": url,
                "source": "arxiv",
                "authors": [
                    " ".join((a.findtext("a:name", "", ATOM) or "").split()) for a in e.findall("a:author", ATOM)
                ],
            }
        )
    return out


def _openalex(client: httpx.Client, title: str) -> list[dict]:
    resp = _get(
        client,
        "https://api.openalex.org/works",
        {
            "search": title,
            "per-page": TOP,
            "select": "title,publication_year,doi",
            "api_key": api_key("OPENALEX_API_KEY"),
        },
    )
    return [
        {
            "title": w.get("title") or "",
            "year": str(w.get("publication_year") or ""),
            "id": w.get("doi") or "",
            "url": w.get("doi") or "",
            "source": "openalex",
            "authors": [],
        }
        for w in resp.json()["results"]
    ]


class SourceLookup:
    """Callable: title -> candidate records from every available source, in source order."""

    def __init__(self, client: httpx.Client | None = None, *, pace: bool = True) -> None:
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
        self.pace = pace
        self.sources = {"crossref": _crossref, "arxiv": _arxiv}
        try:
            api_key("OPENALEX_API_KEY")
            self.sources["openalex"] = _openalex
        except KeyError:
            pass

    def __call__(self, title: str) -> list[dict]:
        found: list[dict] = []
        errors = []
        for name, query in self.sources.items():
            try:
                found += query(self.client, title)
            except (httpx.HTTPError, ET.ParseError, KeyError, ValueError) as exc:
                errors.append(f"{name}: {type(exc).__name__}")
            if self.pace:
                time.sleep(PAUSE[name])
        if errors and len(errors) == len(self.sources):
            raise LookupUnavailable("; ".join(errors))
        return [c for c in found if c["title"]]
