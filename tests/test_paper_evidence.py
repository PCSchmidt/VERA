"""Wider evidence for a paper (RSH-F-14): a superset of the review's passages, within the paper's reading limits."""

from __future__ import annotations

import json
from pathlib import Path

from vera.literature import paper_evidence, reading

QUESTION = "Which information can be recovered from agent traces?"
QUERIES = ["agent trajectory analysis", "design rationale capture"]
TOPICS = [
    "agent traces trajectory", "design rationale", "requirements traceability", "test intent", "repair history",
    "benchmark tasks", "code review", "program repair", "provenance", "debugging replay", "issue logs", "patches",
]  # fmt: skip


def paragraphs(key: str, n: int = 14) -> list[tuple[str, str]]:
    """`n` paragraphs of 40+ words, each about a different topic, so BM25 ranks them differently."""
    out = []
    for i in range(n):
        topic = TOPICS[i % len(TOPICS)]
        words = " ".join(f"{topic} finding {key} {i} word{j}." for j in range(9))
        out.append((f"Section {i // 3}", words))
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def make_review(tmp_path: Path, n_papers: int = 6, review_top: int = 2, no_pdf: tuple[str, ...] = ("R3",)) -> Path:
    """A finished review's files, with the review's read stage reproduced: abstracts for all, full text for the top
    `review_top` with a PDF, 5 ranked passages each."""
    run = tmp_path / "run"
    (run / "artifacts").mkdir(parents=True)
    keys = [f"R{i}" for i in range(1, n_papers + 1)]
    records = [{"key": k, "id": f"arXiv:{k}", "title": f"Paper {k}", "abstract": f"Abstract of {k} about agent traces.",
                "source": "arxiv", "url": "u", "pdf_url": None if k in no_pdf else f"https://x/{k}.pdf"}
               for k in keys]  # fmt: skip
    write_jsonl(run / "retrieved.jsonl", records)
    (run / "scope.json").write_text(json.dumps({"question": QUESTION}), encoding="utf-8")
    (run / "artifacts" / "queries.json").write_text(json.dumps({"question": QUESTION, "queries": QUERIES}), "utf-8")
    query = f"{QUESTION} {' '.join(QUERIES)}"
    passages, papers, full = [], [], 0
    for rec in records:
        passages.append(reading.abstract_passage(rec))
        mode = "abstract"
        if full < review_top and rec["pdf_url"]:
            passages += reading.rank_passages(reading.build_passages(paragraphs(rec["key"]), rec["key"]), query)
            mode, full = "fulltext", full + 1
        papers.append({"key": rec["key"], "title": rec["title"], "mode": mode})
    write_jsonl(run / "passages.jsonl", passages)
    (run / "artifacts" / "reading.json").write_text(json.dumps({"papers": papers}), encoding="utf-8")
    return run


class Fetch:
    def __init__(self, fail: tuple[str, ...] = ()) -> None:
        self.calls: list[str] = []
        self.fail = fail
        self.last_error = None

    def __call__(self, url: str) -> bytes | None:
        self.calls.append(url)
        key = url.rsplit("/", 1)[1].removesuffix(".pdf")
        if key in self.fail:
            self.last_error = "HTTP 404"
            return None
        return key.encode()


def parse(pdf: bytes) -> list[tuple[str, str]]:
    return paragraphs(pdf.decode())


def load(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_RSH_F_14_paper_passages_are_a_superset_of_the_review_with_unchanged_ids(tmp_path: Path) -> None:
    run = make_review(tmp_path)
    review = load(run / "passages.jsonl")
    summary = paper_evidence.widen(run, Fetch(), parse, read_top=4, per_paper=8)
    paper = load(run / "paper" / "passages.jsonl")
    assert paper[: len(review)] == review  # every review passage, unchanged and in order
    assert len({p["id"] for p in paper}) == len(paper)
    assert summary["n_new_passages"] == len(paper) - len(review) > 0
    assert (run / "passages.jsonl").read_text(encoding="utf-8") == "".join(json.dumps(p) + "\n" for p in review)


def test_RSH_F_14_reading_limits_are_respected(tmp_path: Path) -> None:
    run = make_review(tmp_path, n_papers=8)
    fetch = Fetch()
    summary = paper_evidence.widen(run, fetch, parse, read_top=4, per_paper=8)
    paper = load(run / "paper" / "passages.jsonl")
    assert summary["n_full_text"] == 4 and len(fetch.calls) == 4  # R3 has no PDF and is skipped, not fetched
    for key in {p["source_key"] for p in paper}:
        assert sum(1 for p in paper if p["source_key"] == key and p["kind"] == "fulltext") <= 8
    report = json.loads((run / "paper" / "reading.json").read_text(encoding="utf-8"))
    assert [p["mode"] for p in report["papers"]][:5] == ["fulltext", "fulltext", "abstract", "fulltext", "fulltext"]


def test_RSH_F_14_a_failed_fetch_or_parse_falls_back_to_the_abstract_and_says_why(tmp_path: Path) -> None:
    run = make_review(tmp_path)

    def bad_parse(pdf: bytes) -> list[tuple[str, str]]:
        if pdf == b"R4":
            raise RuntimeError("GROBID refused")
        return parse(pdf)

    paper_evidence.widen(run, Fetch(fail=("R2",)), bad_parse, read_top=10, per_paper=8)
    papers = {p["key"]: p for p in json.loads((run / "paper" / "reading.json").read_text("utf-8"))["papers"]}
    assert papers["R2"]["mode"] == "abstract" and "HTTP 404" in papers["R2"]["reason"]
    assert papers["R4"]["mode"] == "abstract" and "GROBID refused" in papers["R4"]["reason"]
    assert papers["R2"]["n_passages"] >= 1  # the review's own passages for R2 stay


def test_RSH_F_14_the_query_is_the_reviews_read_query(tmp_path: Path) -> None:
    run = make_review(tmp_path)
    assert paper_evidence.review_query(run) == f"{QUESTION} {' '.join(QUERIES)}"
