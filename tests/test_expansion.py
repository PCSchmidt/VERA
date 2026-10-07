"""Snowballing from the screened seeds through OpenAlex's reference lists. Recorded responses, no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from vera.literature.expansion import MAX_ADDED, expand, seed_work
from vera.literature.retrieval import HttpCache, Retriever

WORKS = {  # OpenAlex id -> metadata
    f"https://openalex.org/W{n}": {"id": f"https://openalex.org/W{n}", "doi": f"https://doi.org/10.1000/w{n}",
                                   "title": f"Cited paper number {n} on decomposition {'xyz'[n % 3] * 3}",
                                   "publication_year": 2000 + n, "authorships": [],
                                   "abstract_inverted_index": {"Abstract": [0], str(n): [1]}, "best_oa_location": None}
    for n in range(1, 8)
}
SEED_REFS = {  # the seeds' reference lists: W1 and W2 are cited by both seeds, W3-W5 by one, W6 is already known
    "doi:10.48550/arXiv.2510.24815": ["W1", "W2", "W3", "W6"],
    "doi:10.1000/seed2": ["W1", "W2", "W4", "W5"],
}


def make_retriever(requests: list | None = None) -> Retriever:
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        url = str(request.url.copy_with(query=None))
        if "/works/doi:" in url:
            doi = url.split("/works/")[1]
            refs = SEED_REFS.get(doi)
            if refs is None:
                return httpx.Response(404)
            return httpx.Response(200, json={"id": "https://openalex.org/W99", "referenced_works":
                                             [f"https://openalex.org/{r}" for r in refs]})
        wanted = request.url.params["filter"].removeprefix("openalex:").split("|")
        return httpx.Response(200, json={"results": [w for k, w in WORKS.items() if k.rsplit("/", 1)[1] in wanted]})

    return Retriever(httpx.Client(transport=httpx.MockTransport(handler)), pace=False, sources=["openalex"])


@pytest.fixture(autouse=True)
def key(monkeypatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key-123")


SEEDS = [{"key": "R5", "id": "arXiv:2510.24815", "title": "TreeHFD"},
         {"key": "R9", "id": "doi:10.1000/seed2", "title": "Seed two"}]  # fmt: skip
KNOWN = [{"key": f"R{i}", "id": "x", "title": "unrelated", "year": "2020"} for i in range(1, 11)] + [
    {"key": "R11", "id": "doi:10.1000/w6", "title": "Cited paper number 6 on decomposition xxx", "year": "2006"}]


def test_works_cited_by_more_seeds_come_first_and_known_ones_are_not_added() -> None:
    added = expand(make_retriever(), KNOWN, SEEDS, today="2026-10-03")
    titles = [r["title"] for r in added]
    assert len(added) == 5 and not any("number 6" in t for t in titles)  # W6 was already a candidate
    assert {r["cited_by"].__len__() for r in added[:2]} == {2}  # W1 and W2: both seeds cite them
    assert [r["key"] for r in added] == ["R12", "R13", "R14", "R15", "R16"]  # keys continue the existing ones
    assert [r["rank"] for r in added] == [1, 2, 3, 4, 5]
    assert all(r["query"].startswith("cited by R5") or r["query"].startswith("cited by R9") for r in added)
    assert all(r["retrieved"] == "2026-10-03" and r["abstract"] and r["source"] == "openalex" for r in added)


def test_a_seed_openalex_does_not_know_is_skipped_not_fatal() -> None:
    seeds = [{"key": "R5", "id": "arXiv:2510.24815", "title": "t"},
             {"key": "R9", "id": "doi:10.1/unknown", "title": "u"}]  # fmt: skip
    added = expand(make_retriever(), KNOWN, seeds)
    assert {r["cited_by"][0] for r in added} == {"R5"} and len(added) == 3  # W1, W2, W3; W6 is already known
    assert seed_work(make_retriever(), {"key": "R1", "id": "arXiv:odd", "title": "t"}) is None


def test_no_seeds_or_no_reference_lists_add_nothing() -> None:
    assert expand(make_retriever(), KNOWN, []) == []
    assert expand(make_retriever(), KNOWN, [{"key": "R1", "id": "doi:10.1/none", "title": "t"}]) == []


def test_the_expansion_is_capped_and_the_key_stays_out_of_the_cache(tmp_path: Path) -> None:
    many = {f"https://openalex.org/W{n}": {"id": f"https://openalex.org/W{n}", "doi": None,
                                           "title": f"Distinct paper {n} about {n * 7919} {'abcdefgh'[n % 8] * 5}",
                                           "publication_year": 2020, "authorships": [], "abstract_inverted_index": None,
                                           "best_oa_location": None} for n in range(100, 300)}  # fmt: skip

    def handler(request: httpx.Request) -> httpx.Response:
        if "/works/doi:" in str(request.url):
            return httpx.Response(200, json={"id": "https://openalex.org/W1", "referenced_works": list(many)})
        wanted = request.url.params["filter"].removeprefix("openalex:").split("|")
        return httpx.Response(200, json={"results": [w for k, w in many.items() if k.rsplit("/", 1)[1] in wanted]})

    r = Retriever(httpx.Client(transport=httpx.MockTransport(handler)), cache=HttpCache(tmp_path), pace=False,
                  sources=["openalex"])  # fmt: skip
    added = expand(r, [], [{"key": "R1", "id": "doi:10.1/s", "title": "s"}])
    assert len(added) == MAX_ADDED
    stored = " ".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.json"))
    assert stored and "secret-key-123" not in stored
    assert json.loads(json.dumps(added[0]))["key"] == "R1"


def test_a_garbled_reference_year_from_the_parser_does_not_crash_the_snowball() -> None:
    from vera.literature.expansion import _year_gap  # noqa: PLC0415

    assert _year_gap("Apri", "2024") is None and _year_gap("", "2024") is None and _year_gap(None, None) is None
    assert _year_gap("2021", "2024") == 3 and _year_gap("Apr 2022", "2021") == 1  # a year inside text still counts
