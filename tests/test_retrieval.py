"""Retrieval (T5), the relevance screen and the key-paper recall measure, against recorded HTTP fixtures. No network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tests.lit_fakes import LitJudge, make_lit_deps
from vera.audit.bibliography import LookupUnavailable
from vera.literature import retrieval, scoping, stages
from vera.literature.graph import STAGE_NODES, continue_topic_run, start_topic_run
from vera.literature.retrieval import HttpCache, Retriever, merge_records, recall
from vera.schemas import StageResult

RETRIEVAL_NODES = STAGE_NODES[:5]  # queries, retrieve, screen, expand, rescreen: later stages have their own tests
KEYLESS = ["crossref", "arxiv"]  # whatever keys the machine has, the tests use the keyless pair
ARXIV = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry><id>http://arxiv.org/abs/2510.24815v2</id><published>2025-10-28T00:00:00Z</published>
  <title>Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm</title>
  <summary>We decompose tree ensembles.</summary><author><name>Clement Benard</name></author></entry>
 <entry><id>http://arxiv.org/abs/1905.04610v1</id><published>2019-05-11T00:00:00Z</published>
  <title>Explainable AI for Trees: From Local Explanations to Global Understanding</title>
  <summary>TreeSHAP.</summary><author><name>Scott Lundberg</name></author></entry>
</feed>"""
CROSSREF = {"message": {"items": [
    {"title": ["Predictive learning via rule ensembles"], "issued": {"date-parts": [[2008, 9, 1]]},
     "DOI": "10.1214/07-AOAS148", "author": [{"given": "Jerome", "family": "Friedman"}],
     "container-title": ["The Annals of Applied Statistics"], "abstract": "<jats:p>Rule ensembles.</jats:p>"},
    {"title": ["Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm"],
     "issued": {"date-parts": [[2025]]}, "DOI": "10.1000/xyz", "author": []},
]}}


def client(counter: list | None = None, status: list[int] | None = None, fail: set | None = None) -> httpx.Client:
    codes = list(status or [])

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if counter is not None:
            counter.append(host)
        if fail and host in fail:
            return httpx.Response(500, text="boom")
        if codes:
            code = codes.pop(0)
            if code != 200:
                return httpx.Response(code, text="slow down")
        if "arxiv" in host:
            return httpx.Response(200, text=ARXIV)
        return httpx.Response(200, json=CROSSREF)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_each_source_is_parsed_into_records_with_an_abstract_and_a_pdf_link() -> None:
    hits = Retriever(client(), pace=False, sources=KEYLESS)("tree ensemble explainability")
    arxiv = [h for h in hits if h["source"] == "arxiv"]
    assert [h["rank"] for h in arxiv] == [1, 2] and arxiv[0]["id"] == "arXiv:2510.24815"
    assert arxiv[0]["pdf_url"] == "https://arxiv.org/pdf/2510.24815" and arxiv[0]["abstract"]
    crossref = [h for h in hits if h["source"] == "crossref"]
    assert crossref[0]["id"] == "doi:10.1214/07-AOAS148" and crossref[0]["abstract"] == "Rule ensembles."
    assert crossref[0]["venue"] == "The Annals of Applied Statistics" and crossref[0]["year"] == "2008"
    assert all(h["query"] == "tree ensemble explainability" for h in hits)


def test_a_cached_response_is_not_requested_again_and_carries_its_url_and_date(tmp_path: Path) -> None:
    calls: list = []
    r = Retriever(client(calls), cache=HttpCache(tmp_path), pace=False, sources=KEYLESS)
    first = r("rule ensembles")
    n = len(calls)
    assert n == 2  # crossref and arxiv, once each
    assert r("rule ensembles") == first and len(calls) == n  # the rerun made no request
    entry = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert entry["url"].startswith("https://") and len(entry["retrieved"]) == 10 and entry["text"]


def test_requests_are_paced_and_a_rate_limit_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(retrieval.time, "sleep", sleeps.append)
    clock = iter(range(0, 1000))  # the clock advances 1 s per reading
    r = Retriever(client(status=[429, 200]), pace=True, now=lambda: float(next(clock)), sources=KEYLESS)
    r("a query")
    assert any(s >= 3 for s in sleeps)  # backed off after the 429, and arXiv's 3.1 s pause was applied
    assert max(sleeps) >= 3.0


def test_a_failing_source_is_skipped_and_all_failing_is_an_error() -> None:
    hits = Retriever(client(fail={"api.crossref.org"}), pace=False, sources=KEYLESS)("q")
    assert {h["source"] for h in hits} == {"arxiv"}
    with pytest.raises(LookupUnavailable):
        Retriever(client(fail={"api.crossref.org", "export.arxiv.org"}), pace=False, sources=KEYLESS)("q")


def test_records_are_deduplicated_across_sources_and_ranked_by_best_rank() -> None:
    hits = Retriever(client(), pace=False, sources=KEYLESS)("tree ensemble explainability")
    hits += [{**h, "query": "another query", "rank": 1} for h in hits if h["id"] == "arXiv:1905.04610"]
    merged = merge_records(hits, today="2026-10-03")
    titles = [m["title"] for m in merged]
    assert len(titles) == len(set(titles)) == 3  # the Crossref copy of TreeHFD merged into the arXiv record
    parts = merge_records([{**hits[0], "title": "Learning trees, part I", "id": "x1", "rank": 1},
                           {**hits[0], "title": "Learning trees, part II", "id": "x2", "rank": 2}])
    assert len(parts) == 2  # near-identical titles that differ by a numeral stay two papers
    assert [m["key"] for m in merged] == ["R1", "R2", "R3"]
    treehfd = next(m for m in merged if m["title"].startswith("Tree Ensemble"))
    assert treehfd["id"] == "arXiv:2510.24815" and treehfd["abstract"] and treehfd["hits"] == 2
    seen_twice = next(m for m in merged if m["id"] == "arXiv:1905.04610")
    assert seen_twice["n_queries"] == 2 and seen_twice["rank"] == 1
    assert all(m["retrieved"] == "2026-10-03" for m in merged)
    assert [(m["rank"], -m["n_queries"]) for m in merged] == sorted((m["rank"], -m["n_queries"]) for m in merged)


KEY_PAPERS = [
    {"title": "Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm",
     "id": "arXiv:2510.24815"},
    {"title": "Predictive learning via rule ensembles", "id": "doi:10.1214/07-AOAS148"},
    {"title": "A paper the retrieval never found", "id": "arXiv:9999.00001"},
]


def test_recall_counts_key_papers_before_and_after_the_screen_and_in_the_top_n() -> None:
    records = merge_records(Retriever(client(), pace=False, sources=KEYLESS)("q"))
    r1 = next(r["key"] for r in records if r["id"] == "arXiv:2510.24815")
    result = recall(KEY_PAPERS, records, kept={r1}, top_n=1)
    assert result["n_key_papers"] == 3 and result["found"] == pytest.approx(2 / 3)
    assert result["kept"] == pytest.approx(1 / 3) and result["in_top"] == pytest.approx(1 / 3)
    rows = {r["id"]: r for r in result["rows"]}
    assert rows["arXiv:2510.24815"]["kept"] and not rows["doi:10.1214/07-AOAS148"]["kept"]
    assert not rows["arXiv:9999.00001"]["found"] and rows["arXiv:9999.00001"]["key"] is None
    # a key paper is also matched by a near-identical title when the identifiers differ
    near = {"title": "Predictive Learning via Rule Ensembles.", "id": "doi:other"}
    assert any(retrieval.matches(near, r) for r in records)


# ── the stage nodes ─────────────────────────────────────────────────────────────────────────────────


WORDS = ["Boosting", "Forest", "Shapley", "Interaction", "Additive", "Variance", "Sobol", "Marginal", "Conditional",
         "Permutation", "Surrogate", "Hierarchical"]


class FakeRetriever:
    def __init__(self, n: int = 8, shift: int = 0, sources: tuple = ("crossref", "arxiv")) -> None:
        self.n, self.shift, self.queries, self.sources = n, shift, [], list(sources)

    def __call__(self, query: str) -> list[dict]:
        self.queries.append(query)
        return [{"title": f"{WORDS[(i + self.shift) % len(WORDS)]} approach to {query}",
                 "authors": ["A. Author"], "year": "2024",
                 "id": f"arXiv:2401.{i:05d}", "url": f"https://arxiv.org/abs/2401.{i:05d}",
                 "abstract": f"Abstract {i}.", "pdf_url": None, "source": "arxiv", "query": query, "rank": i + 1}
                for i in range(self.n)]  # fmt: skip


def literature_run(tmp_path: Path, *, judge=None, retriever=None, replies=None):
    queries = '```json\n["tree explainability", "functional decomposition", "tree explainability"]\n```'
    deps = make_lit_deps(tmp_path, replies={"p3.retrieve": queries} | (replies or {}))
    if judge is not None:
        deps.judge = judge(deps)
    deps.extra["retriever"] = retriever or FakeRetriever()
    start_topic_run(deps, extra_nodes=RETRIEVAL_NODES)
    scoping.confirm_scope(deps.run_dir, "Chris")
    return deps, continue_topic_run(deps, extra_nodes=RETRIEVAL_NODES)


def test_queries_are_parsed_deduplicated_and_capped() -> None:
    reply = '["a b c", "A B C", "second query", "third"]'
    assert stages.parse_queries(reply) == ["a b c", "second query", "third"]
    assert stages.parse_queries("no list here") == []
    assert len(stages.parse_queries(json.dumps([f"query {i}" for i in range(20)]))) == stages.N_QUERIES


def test_the_retrieval_stage_logs_every_candidate_and_screens_them(tmp_path: Path) -> None:
    deps, state = literature_run(tmp_path)
    assert state["trail"][-5:] == ["queries", "retrieve", "screen", "expand", "rescreen"]
    assert not state.get("stop") and "no OpenAlex key" in state["expansion"]["skipped"]
    assert deps.extra["retriever"].queries == ["tree explainability", "functional decomposition"]  # deduplicated
    log = [json.loads(ln) for ln in (deps.run_dir / "retrieved.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(log) == 8 and log[0]["key"] == "R1" and all(r["query"] and r["rank"] for r in log)
    assert state["kept"] == [r["key"] for r in log]  # the fake judge says yes to every candidate
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "retrieve")
    assert sr.decision == "accept" and len(sr.gates) == 8 and all(g.question_id == "lit.relevant" for g in sr.gates)
    assert sr.metrics["n_kept"] == 8.0 and sr.producer_id == "p3.retrieve"


def test_a_screen_verdict_is_never_paid_for_twice(tmp_path: Path) -> None:
    deps, _ = literature_run(tmp_path)
    asked = deps.judge.asked.count("lit.relevant")
    assert asked == 8
    state = stages.screen_node(deps)({})  # run the node again: every verdict is in screen.jsonl
    assert deps.judge.asked.count("lit.relevant") == asked and len(state["kept"]) == 8


def test_unsure_and_negative_verdicts_are_not_kept(tmp_path: Path) -> None:
    class Picky(LitJudge):
        def ask(self, state, questions):
            out = super().ask(state, questions)
            if questions[0].id != "lit.relevant":
                return out
            n = self.asked.count("lit.relevant")  # 1, 2, 3, ...: every other one says yes, the third is unsure
            return [v.model_copy(update={"answer": n % 2 == 0, "confidence": 0.3 if n == 3 else 0.9}) for v in out]

    deps, state = literature_run(tmp_path, judge=lambda d: Picky(d.ledger, d.budget), retriever=FakeRetriever(12))
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "retrieve")
    assert sr.metrics["n_screened"] == 12.0 and sr.metrics["n_kept"] == 6.0 and sr.metrics["n_unsure"] == 1.0
    assert sr.decision == "accept"  # six relevant candidates is enough (the minimum is five)


def test_too_few_relevant_candidates_stop_the_stage(tmp_path: Path) -> None:
    deps, state = literature_run(
        tmp_path, judge=lambda d: LitJudge(d.ledger, d.budget, answers={"lit.relevant": False})
    )
    assert state["stop"]["stage"] == "retrieve" and "only 0 relevant" in state["stop"]["reason"]
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "retrieve")
    assert sr.decision == "reject" and sr.reason and "need 5" in sr.reason


def test_retrieval_needs_a_confirmed_question_and_usable_queries(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path, replies={"p3.retrieve": "I have no queries."})
    deps.extra["retriever"] = FakeRetriever()
    start_topic_run(deps, extra_nodes=RETRIEVAL_NODES)
    with pytest.raises(scoping.ScopeNotConfirmedError):
        stages.queries_node(deps)({})  # nothing is retrieved for a question nobody confirmed
    scoping.confirm_scope(deps.run_dir, "Chris")
    state = continue_topic_run(deps, extra_nodes=RETRIEVAL_NODES)
    assert "no usable search queries" in state["stop"]["reason"] and deps.extra["retriever"].queries == []


def test_no_source_answering_stops_the_stage(tmp_path: Path) -> None:
    def down(query: str):
        raise LookupUnavailable("crossref: ConnectError; arxiv: ConnectError")

    deps, state = literature_run(tmp_path, retriever=down)
    assert state["stop"]["stage"] == "retrieve" and "no bibliographic source" in state["stop"]["reason"]


# ── v2: papers only from Crossref, OpenAlex primary when the user has a key ─────────────────────────

OPENALEX = {"results": [
    {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/abc", "title": "TreeSHAP revisited",
     "publication_year": 2022, "authorships": [{"author": {"display_name": "A. Author"}}],
     "abstract_inverted_index": {"We": [0], "revisit": [1], "TreeSHAP": [2]},
     "best_oa_location": {"pdf_url": "https://example.org/w1.pdf"}},
    {"id": "https://openalex.org/W2", "doi": None, "title": "No open access here", "publication_year": 2020,
     "authorships": [], "abstract_inverted_index": None, "best_oa_location": None},
]}


def test_crossref_is_asked_for_papers_only_and_the_request_says_so() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=ARXIV) if "arxiv" in request.url.host else httpx.Response(200, json=CROSSREF)

    r = Retriever(httpx.Client(transport=httpx.MockTransport(handler)), pace=False, sources=KEYLESS)
    r("tree explainability")
    crossref = next(q for q in seen if "crossref" in q.url.host)
    assert "type%3Ajournal-article" in str(crossref.url) and "type%3Aposted-content" in str(crossref.url)
    assert "component" not in str(crossref.url)  # figure and table captions are not papers


def test_openalex_records_carry_the_reconstructed_abstract_and_the_open_access_pdf(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)  # a real .env must not change what the test sees
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key-123")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=OPENALEX)

    r = Retriever(httpx.Client(transport=httpx.MockTransport(handler)), pace=False)
    assert r.sources[0] == "openalex" and r.sources[1:] == ["crossref", "arxiv"]  # primary when the user has a key
    found = [h for h in retrieval._openalex_records(json.dumps(OPENALEX), "q")]
    assert found[0]["abstract"] == "We revisit TreeSHAP" and found[0]["pdf_url"] == "https://example.org/w1.pdf"
    assert found[0]["id"] == "doi:10.1000/abc" and found[1]["abstract"] is None and found[1]["pdf_url"] is None


def test_a_key_is_never_written_to_the_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key-123")
    r = Retriever(httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=OPENALEX))),
                  cache=HttpCache(tmp_path), pace=False, sources=["openalex"])  # fmt: skip
    r("tree explainability")
    stored = " ".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.json"))
    assert stored and "secret-key-123" not in stored


def test_without_a_key_the_sources_are_the_keyless_pair(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)  # no .env there either
    assert Retriever(pace=False).sources == ["crossref", "arxiv"]


def test_a_stopped_stage_can_be_rerun_from_its_checkpoint_in_the_same_run(tmp_path: Path) -> None:
    from vera.literature.graph import rerun_from  # noqa: PLC0415

    class Fussy(LitJudge):  # says no to everything on the first pass
        say = False

        def ask(self, state, questions):
            out = super().ask(state, questions)
            if questions[0].id != "lit.relevant":
                return out
            return [v.model_copy(update={"answer": self.say}) for v in out]

    deps, first = literature_run(tmp_path, judge=lambda d: Fussy(d.ledger, d.budget))
    assert first["stop"]["stage"] == "retrieve"
    spent_before, records_before = deps.budget.spent_usd, len(deps.ledger.records())
    deps.judge.say = True  # the stage's code (here: the judge's answers) has changed
    deps.extra["retriever"] = FakeRetriever(8, shift=4)  # a better retrieval: different candidates
    second = rerun_from(deps, "queries", extra_nodes=RETRIEVAL_NODES)
    assert not second.get("stop") and len(second["kept"]) == 8
    assert len(deps.ledger.records()) > records_before and deps.budget.spent_usd > spent_before  # appended, not reset
    gates = (deps.run_dir / "gates.jsonl").read_text(encoding="utf-8")
    assert gates.count('"answer": false') >= 8 and gates.count('"answer": true') >= 9  # both attempts are on record
    assert scoping.read_scope(deps.run_dir).status == "confirmed"  # the confirmation was kept, not asked again
    import pytest  # noqa: PLC0415

    with pytest.raises(LookupError):
        rerun_from(deps, "no_such_node", extra_nodes=RETRIEVAL_NODES)


def test_the_expansion_adds_the_seeds_references_and_the_new_candidates_are_screened(tmp_path: Path) -> None:
    added_records = [{"title": f"Cited work {w} on trees", "authors": [], "year": "2010", "id": f"doi:10.1/{w}",
                      "url": f"https://doi.org/10.1/{w}", "abstract": f"Cites {w}.", "pdf_url": None,
                      "source": "openalex", "query": "cited by R1, R2", "rank": i + 1, "key": f"R{9 + i}",
                      "retrieved": "2026-10-03", "cited_by": ["R1", "R2"]} for i, w in enumerate("abcd")]  # fmt: skip
    seen: dict = {}

    def fake_expand(retriever, records, seeds, references_of=None):
        seen["seeds"] = [s["key"] for s in seeds]
        return added_records

    queries = '```json\n["tree explainability", "functional decomposition"]\n```'
    deps = make_lit_deps(tmp_path, replies={"p3.retrieve": queries})
    deps.extra |= {"retriever": FakeRetriever(8, sources=("openalex", "crossref", "arxiv")), "expand": fake_expand}
    start_topic_run(deps, extra_nodes=RETRIEVAL_NODES)
    scoping.confirm_scope(deps.run_dir, "Chris")
    state = continue_topic_run(deps, extra_nodes=RETRIEVAL_NODES)
    log = [json.loads(ln) for ln in (deps.run_dir / "retrieved.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(log) == 12 and log[-1]["key"] == "R12" and log[-1]["cited_by"] == ["R1", "R2"]
    assert state["expansion"] == {"seeds": seen["seeds"], "added": 4} and len(seen["seeds"]) == 5
    assert len(state["kept"]) == 12 and state["trail"][-2:] == ["expand", "rescreen"]
    assert deps.judge.asked.count("lit.relevant") == 12  # the first screen's eight verdicts were not paid for twice
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "retrieve")
    assert len(sr.gates) == 12  # the stage's record holds every verdict, old and new


def test_the_expansion_needs_two_seeds_and_a_key(tmp_path: Path) -> None:
    deps, state = literature_run(tmp_path, judge=lambda d: LitJudge(d.ledger, d.budget,
                                                                    answers={"lit.relevant": False}))
    assert state["expansion"]["skipped"].startswith("no OpenAlex key") or "seeds" in state["expansion"]["skipped"]
    assert state["stop"]["reason"].startswith("gate: only 0 relevant")  # the stage gate is the second screen


# ── Increment 5: Semantic Scholar as a second keyed source (T5 reverse-if (5)) ───────────────────────

S2 = {"data": [
    {"paperId": "p1", "title": "TreeHFD  decomposition", "year": 2025, "authors": [{"name": "B. Author"}],
     "abstract": "We decompose.", "venue": "NeurIPS", "externalIds": {"ArXiv": "2510.00001", "DOI": "10.1/x"},
     "openAccessPdf": {"url": "https://arxiv.org/pdf/2510.00001"}},
    {"paperId": "p2", "title": "Only an S2 id", "year": None, "authors": [], "abstract": None, "venue": "",
     "externalIds": {}, "openAccessPdf": None},
]}


def test_semantic_scholar_is_a_source_only_with_the_users_key_and_comes_last(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "s2-secret-456")
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)
    assert Retriever(pace=False).sources == ["crossref", "arxiv", "semanticscholar"]
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY")
    assert Retriever(pace=False).sources == ["crossref", "arxiv"]  # unchanged without a key


def test_semantic_scholar_records_and_the_key_goes_in_a_header_never_the_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "s2-secret-456")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=S2)

    r = Retriever(httpx.Client(transport=httpx.MockTransport(handler)), cache=HttpCache(tmp_path), pace=False,
                  sources=["semanticscholar"])  # fmt: skip
    found = r("tree explainability")
    assert seen[0].headers["x-api-key"] == "s2-secret-456" and "s2-secret-456" not in str(seen[0].url)
    assert found[0]["id"] == "arXiv:2510.00001" and found[0]["title"] == "TreeHFD decomposition"
    assert found[0]["pdf_url"] == "https://arxiv.org/pdf/2510.00001" and found[0]["source"] == "semanticscholar"
    assert found[1]["id"] == "s2:p2" and found[1]["abstract"] is None and found[1]["pdf_url"] is None
    assert "s2-secret-456" not in " ".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.json"))
