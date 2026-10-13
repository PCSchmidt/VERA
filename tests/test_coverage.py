# ruff: noqa: E501
"""RSH-F-16: a targeted search for works a paper names (Increment 6's third paper never retrieved the Context Language
Models paper Chris pasted into its emphasis). No network: a fake search client."""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_paper_evidence import Fetch, make_review, parse
from tests.test_paper_stage import STATS, run_nodes, script, setup_run
from vera.literature import coverage, paper_evidence
from vera.schemas import PaperDocument, PaperRequest

ROOT = Path(__file__).resolve().parents[1]
CLM = {"key": "?", "id": "arXiv:2610.01234", "title": "Context Language Models", "authors": ["Rulin Shao", "Pang Wei Koh"],
       "abstract": "We introduce Context Language Models.", "source": "arxiv", "url": "https://arxiv.org/abs/2610.01234",
       "pdf_url": "https://x/CLM.pdf"}  # fmt: skip


class Search:
    """A fake search client: returns `hits` for any query and records the queries."""

    def __init__(self, hits: list[dict] | None = None) -> None:
        self.hits, self.queries = hits if hits is not None else [CLM], []

    def __call__(self, query: str) -> list[dict]:
        self.queries.append(query)
        return list(self.hits)


def test_RSH_F_16_works_named_in_the_emphasis_are_read_from_it() -> None:
    emphasis = json.loads((ROOT / "data/paper_demo/rlm-vs-clm-3/paper/request.json").read_text(encoding="utf-8"))["emphasis"]
    targets = coverage.named_targets("How do RLMs and CLMs differ?", emphasis)
    assert targets[0] == {"kind": "title", "query": "Context Language Models", "title": "Context Language Models", "author": "Shao"}
    more = coverage.named_targets("See arXiv:2512.24601 and the work of Zhang et al. on recursion.", None)
    assert [(t["kind"], t["query"]) for t in more] == [("arxiv", "2512.24601"), ("author", "Zhang")]
    assert coverage.named_targets("How do recursive and context-centric models differ?", "") == []


def test_RSH_F_16_a_named_work_is_looked_up_once_and_added_under_a_new_key() -> None:
    records = {"R1": {"key": "R1", "title": "Recursive Language Models", "authors": ["A. Zhang"]}, "R7": {"key": "R7", "title": "x"}}
    targets = coverage.named_targets('"Recursive Language Models" and "Context Language Models"', None)
    search = Search()
    report, added = coverage.lookup(targets, records, search)
    assert [t["outcome"] for t in report] == ["already a source", "found"]
    assert report[0]["key"] == "R1" and search.queries == ["Context Language Models"]  # one lookup, for the missing work
    assert added[0]["key"] == "R8" and added[0]["title"] == "Context Language Models" and report[1]["key"] == "R8"


def test_RSH_F_16_a_miss_is_reported_and_lookups_stop_at_the_limit() -> None:
    targets = coverage.named_targets('"Alpha Beta Gamma" "Delta Epsilon Zeta" "Eta Theta Iota" "Kappa Lambda Mu"', None)
    search = Search(hits=[{"title": "Something else entirely", "authors": []}])
    report, added = coverage.lookup(targets, {}, search)
    assert [t["outcome"] for t in report] == ["not found", "not found", "not found", "not searched"]
    assert len(search.queries) == coverage.MAX_LOOKUPS == 3 and added == []
    assert "limit of 3" in report[3]["why"]
    none, _ = coverage.lookup(targets[:1], {}, None)
    assert none[0]["outcome"] == "not searched" and none[0]["why"] == "no search client"
    by_author = coverage.named_targets("work by Shao and colleagues", None)
    report, added = coverage.lookup(by_author, {}, Search(hits=[{**CLM, "authors": ["Someone Else"]}, CLM]), question="context models")
    assert report[0]["outcome"] == "found" and added[0]["authors"] == CLM["authors"]  # only a hit by that author counts


def test_RSH_F_16_a_found_work_is_read_first_and_the_review_passages_stay(tmp_path: Path) -> None:
    run = make_review(tmp_path)
    review = (run / "passages.jsonl").read_text("utf-8").splitlines()
    added = [{**CLM, "key": "R7"}]
    summary = paper_evidence.widen(run, Fetch(), parse, added=added)
    passages = [json.loads(ln) for ln in (run / "paper" / "passages.jsonl").read_text("utf-8").splitlines()]
    assert [json.dumps(p) for p in passages[: len(review)]] == [json.dumps(json.loads(ln)) for ln in review]  # a superset
    assert any(p["source_key"] == "R7" for p in passages)
    reading = json.loads((run / "paper" / "reading.json").read_text("utf-8"))
    assert reading["papers"][0]["key"] == "R7" and reading["papers"][0]["mode"] == "fulltext"
    assert summary["n_full_text"] >= 1 and not (run / "retrieved.jsonl").read_text("utf-8").count("Context Language Models")


def test_RSH_F_16_the_paper_says_what_it_searched_for(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    deps.extra["paper_request"] = PaperRequest(max_usd=1.0, emphasis='Relate it to "Context Language Models" and "Missing Work Title Here".')
    deps.extra["retriever"] = Search()
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    report = json.loads((run / "paper" / "coverage.json").read_text("utf-8"))["targets"]
    assert [t["outcome"] for t in report] == ["found", "not found"]
    new_key = report[0]["key"]
    assert json.loads((run / "paper" / "added_records.jsonl").read_text("utf-8").splitlines()[0])["key"] == new_key
    script(deps, run)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    assert not state.get("stop"), state.get("stop")
    doc = PaperDocument.model_validate(state["paper"])
    threats = next(s.text for s in doc.sections if s.heading == "Threats to validity")
    assert "“Context Language Models” was found by a targeted search" in threats
    assert "“Missing Work Title Here” was searched for and not found" in threats
    assert new_key not in (run / "retrieved.jsonl").read_text("utf-8")  # the review's file is unchanged
