"""Reading: PDFs to evidence passages, the quote check, the cache and the read stage. Recorded fixtures, no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from tests.lit_fakes import LitJudge
from tests.test_retrieval import FakeRetriever
from vera.literature import reading, stages
from vera.literature.graph import STAGE_NODES
from vera.literature.reading import ParseCache, PdfFetcher, build_passages, quote_in_text, rank_passages
from vera.schemas import StageResult

THROUGH_READING = STAGE_NODES[:7]  # queries ... read_gate

TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
 <div><head>Introduction</head>
  <p>Tree ensembles are accurate but hard to interpret. We study how a functional decomposition behaves when the input
  features are correlated, and we compare it with Shapley-based attributions on synthetic data with known components.
  The decomposition assigns every prediction to main effects and interactions.</p></div>
 <div><head>Results</head>
  <p>When the correlation between two features rises above 0.9, the estimated interaction between them becomes
  unstable across bootstrap refits, while the main effects remain close to the ground truth in our experiments.</p>
  <p>Short.</p></div>
 <div><head>References</head><p>Lundberg, S. et al. A unified approach to interpreting model predictions.</p></div>
</body></text></TEI>"""
PDF = b"%PDF-1.5 fake"


def test_quotes_are_checked_after_normalisation() -> None:
    text = "The decomposition becomes unsta-\nble when the corre­lation of two features rises above 0.9."
    assert quote_in_text("the decomposition becomes unstable when the correlation of two features", text)
    curly = "He said “the decomposition becomes unstable” when the correlation of two features rises."
    assert quote_in_text('said "the decomposition becomes unstable" when the correlation', curly)  # quotation marks
    assert not quote_in_text("the decomposition becomes stable when the correlation of two features", text)  # altered
    assert not quote_in_text("rises above 0.9", text)  # real, but too short to prove anything
    assert not quote_in_text("a sentence the passage never contained, of sufficient length", text)
    assert quote_in_text("ﬁrst-order eﬀects are estimated by a decomposition of", "First-order effects are "
                         "estimated by a decomposition of the model.")  # ligatures


def test_tei_paragraphs_keep_their_section_heads_and_references_are_skipped() -> None:
    paragraphs = reading.paragraphs_from_tei(TEI)
    assert [h for h, _ in paragraphs] == ["Introduction", "Results", "Results", "References"]
    passages = build_passages(paragraphs, "R3")
    assert passages and all(p["source_key"] == "R3" and p["kind"] == "fulltext" for p in passages)
    assert [p["id"] for p in passages] == [f"R3-P{i}" for i in range(1, len(passages) + 1)]
    assert all("Lundberg" not in p["text"] for p in passages)  # the reference list is not evidence
    assert passages[0]["locator"].startswith("sec. Introduction, para 1")
    assert all(len(p["text"].split()) <= reading.MAX_PASSAGE_WORDS for p in passages)


def test_the_passages_most_relevant_to_the_question_come_first() -> None:
    passages = build_passages(reading.paragraphs_from_tei(TEI), "R3")
    best = rank_passages(passages, "interaction stability when features are strongly correlated", top=1)
    assert len(best) == 1 and "unstable across bootstrap" in best[0]["text"]
    assert rank_passages([], "anything") == []


def test_a_long_paragraph_is_cut_at_sentence_boundaries() -> None:
    sentences = " ".join(f"Sentence number {i} says something about trees and forests in detail." for i in range(60))
    passages = build_passages([("Method", sentences)], "R1")
    assert len(passages) > 1 and all(len(p["text"].split()) <= reading.MAX_PASSAGE_WORDS for p in passages)
    assert "".join(p["text"] for p in passages).replace(" ", "") == sentences.replace(" ", "")


def mock_client(responses: list[httpx.Response], seen: list | None = None) -> httpx.Client:
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_pdf_is_fetched_once_and_cached(tmp_path: Path) -> None:
    seen: list = []
    fetch = PdfFetcher(tmp_path, mock_client([httpx.Response(200, content=PDF)], seen), pace=False)
    assert fetch("https://arxiv.org/pdf/2510.24815") == PDF and fetch("https://arxiv.org/pdf/2510.24815") == PDF
    assert len(seen) == 1  # the second call came from the cache


def test_a_missing_or_non_pdf_response_is_reported_not_raised(tmp_path: Path) -> None:
    fetch = PdfFetcher(tmp_path, mock_client([httpx.Response(404)]), pace=False)
    assert fetch("https://x/y.pdf") is None and fetch.last_error == "HTTP 404"
    fetch = PdfFetcher(tmp_path / "b", mock_client([httpx.Response(200, content=b"<html>login</html>")]), pace=False)
    assert fetch("https://x/z.pdf") is None and "not a PDF" in fetch.last_error
    fetch = PdfFetcher(tmp_path / "c", mock_client([httpx.Response(429), httpx.Response(200, content=PDF)]), pace=False)
    assert fetch("https://x/w.pdf") == PDF  # a rate limit is retried


def test_a_parse_is_cached_by_the_pdfs_hash_and_the_parser(tmp_path: Path) -> None:
    calls: list = []

    class Parser:
        name = "fake-1"

        def __call__(self, pdf: bytes):
            calls.append(1)
            return [("Intro", "text")]

    cache = ParseCache(tmp_path)
    assert cache.parse(PDF, Parser()) == [("Intro", "text")] and cache.parse(PDF, Parser()) == [("Intro", "text")]
    assert len(calls) == 1
    Parser.name = "fake-2"
    cache.parse(PDF, Parser())
    assert len(calls) == 2  # a different parser is not served the first one's parse


# ── the read stage ──────────────────────────────────────────────────────────────────────────────────


class Fetch:
    def __init__(self, fail_for: set | None = None, none_for: set | None = None) -> None:
        self.calls, self.fail_for, self.none_for, self.last_error = [], fail_for or set(), none_for or set(), None

    def __call__(self, url: str):
        self.calls.append(url)
        if url in self.none_for:
            self.last_error = "HTTP 404"
            return None
        if url in self.fail_for:
            raise RuntimeError("network down")
        return PDF


class Records(FakeRetriever):
    """Candidates with a PDF link, except R-odd ones that have none."""

    def __call__(self, query: str) -> list[dict]:
        out = super()(query) if False else FakeRetriever.__call__(self, query)
        for r in out:
            r["pdf_url"] = f"https://arxiv.org/pdf/{r['id'].split(':')[1]}" if r["rank"] % 2 else None
        return out


def read_run(tmp_path: Path, *, fetch=None, parse=None, read_top: int = 2, judge=None):
    def extras(deps) -> None:
        deps.extra |= {"fetch_pdf": fetch or Fetch(), "read_top": read_top,
                       "parse_pdf": parse or (lambda pdf: reading.paragraphs_from_tei(TEI))}  # fmt: skip

    from tests.lit_fakes import make_lit_deps  # noqa: PLC0415
    from tests.test_retrieval import FakeRetriever as _F  # noqa: PLC0415
    from vera.literature import scoping  # noqa: PLC0415
    from vera.literature.graph import continue_topic_run, start_topic_run  # noqa: PLC0415

    queries = '```json\n["tree explainability", "functional decomposition"]\n```'
    deps = make_lit_deps(tmp_path, replies={"p3.retrieve": queries})
    if judge:
        deps.judge = judge(deps)
    deps.extra["retriever"] = Records(8) if _F else None
    extras(deps)
    start_topic_run(deps, extra_nodes=THROUGH_READING)
    scoping.confirm_scope(deps.run_dir, "Chris")
    return deps, continue_topic_run(deps, extra_nodes=THROUGH_READING)


def passages_of(deps) -> list[dict]:
    return [json.loads(ln) for ln in (deps.run_dir / "passages.jsonl").read_text(encoding="utf-8").splitlines()]


def test_the_read_stage_reads_the_top_k_in_full_and_the_rest_by_abstract(tmp_path: Path) -> None:
    fetch = Fetch()
    deps, state = read_run(tmp_path, fetch=fetch, read_top=2)
    assert state["trail"][-2:] == ["read", "read_gate"] and not state.get("stop")
    report = {r["key"]: r for r in state["read_report"]}
    full = [k for k, r in report.items() if r["mode"] == "fulltext"]
    assert len(full) == 2 and len(fetch.calls) == 2  # only the top K were fetched
    assert sum(r["mode"] == "abstract" for r in report.values()) == 6  # the rest: abstract only
    passages = passages_of(deps)
    assert {p["source_key"] for p in passages} == set(report)  # every kept candidate has some evidence
    assert all(p["locator"] and p["text"] for p in passages)
    assert sum(p["kind"] == "abstract" for p in passages) == 8  # abstracts for all
    assert all(p["id"].startswith(p["source_key"]) for p in passages)


def test_a_failed_download_or_parse_falls_back_to_the_abstract_and_says_why(tmp_path: Path) -> None:
    fetch = Fetch(none_for={"https://arxiv.org/pdf/2401.00000"}, fail_for={"https://arxiv.org/pdf/2401.00002"})
    deps, state = read_run(tmp_path, fetch=fetch, read_top=4)
    reasons = {r["key"]: r.get("reason") for r in state["read_report"] if r.get("reason")}
    assert any("no PDF: HTTP 404" in v for v in reasons.values())
    assert any("RuntimeError: network down" in v for v in reasons.values())
    full = [r for r in state["read_report"] if r["mode"] == "fulltext"]
    assert len(full) == 2  # four candidates had a PDF; two failed, and the stage read the other two in full


def test_a_parser_that_returns_nothing_is_reported(tmp_path: Path) -> None:
    deps, state = read_run(tmp_path, parse=lambda pdf: [], read_top=2)
    assert all(r["mode"] == "abstract" for r in state["read_report"])
    assert any("no usable body text" in (r.get("reason") or "") for r in state["read_report"])


def test_the_read_gate_rejects_thin_evidence(tmp_path: Path) -> None:
    deps, state = read_run(tmp_path, judge=lambda d: LitJudge(d.ledger, d.budget,
                                                              answers={"lit.evidence_sufficient": False}))
    assert state["stop"]["stage"] == "read" and "sufficient" in state["stop"]["reason"]
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "read")
    assert sr.decision == "reject" and sr.reason and sr.gate.question_id == "lit.evidence_sufficient"


def test_reading_again_makes_no_fetch_or_parse_calls_when_cached(tmp_path: Path) -> None:
    fetch = Fetch()
    deps, state = read_run(tmp_path, fetch=fetch)
    n = len(fetch.calls)
    update = stages.read_node(deps)({"kept": state["kept"], "queries": state["queries"]})
    assert update["passages"] == len(passages_of(deps))
    assert len(fetch.calls) == n * 2  # the stage itself does not cache: the fetcher and the parser do (tests above)


def test_the_passages_are_the_only_evidence_the_gate_sees(tmp_path: Path) -> None:
    deps, state = read_run(tmp_path)
    gate = [json.loads(ln) for ln in (deps.run_dir / "gates.jsonl").read_text(encoding="utf-8").splitlines()]
    sufficient = [g for g in gate if g["question"]["id"] == "lit.evidence_sufficient"]
    assert len(sufficient) == 1 and "Evidence gathered (8 papers)" in sufficient[0]["material"]


def test_references_from_an_empty_grobid_answer_is_an_empty_list() -> None:
    from vera.literature.reading import references_from_tei

    assert references_from_tei("") == []
    assert references_from_tei("   ") == []
