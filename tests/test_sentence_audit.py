# ruff: noqa: E501
"""AUD-F-12: the audit lists every sentence of a review or a paper's evidence sections and re-checks each.

Uses the defects Increment 6's green audits missed, a fake judge, and the three Increment 6 papers (read, never
written: the audits that write run on copies)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge
from tests.test_paper_evidence import make_review
from tests.test_paper_pipeline import finish_review, make_deps, script
from vera.app import pipeline
from vera.app.pdf import render_pdf
from vera.audit import sentences
from vera.schemas import PaperRequest, Question, Verdict

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = {
    "C1": {"claim": "The trajectory study links longer trajectories to failure.", "source_key": "R2", "title": "Trajectory failures",
           "quote": "Longer trajectories were associated with failure in the analysed runs of coding agents."},
    "C2": {"claim": "The trajectory study finds failed runs used more steps.", "source_key": "R2", "title": "Trajectory failures",
           "quote": "Failed runs used more steps than successful runs across all of the analysed repositories."},
    "C3": {"claim": "The externalization review calls the harness a structured form of context engineering.", "source_key": "R87",
           "title": "Externalization in LLM Agents", "quote": "The harness separates the prompt into layers with distinct update rates."},
    "C4": {"claim": "The SWE-agent study warns its patch may overfit.", "source_key": "R1", "title": "SWE-agent study",
           "quote": "However, this patch may be overfitting to the added tests."},
}  # fmt: skip


class Says:
    """An `ask` that answers True unless the material holds one of `no[question id]`, with confidence 0.9."""

    def __init__(self, no: dict[str, tuple[str, ...]] | None = None, unsure: tuple[str, ...] = ()) -> None:
        self.no, self.unsure, self.asked = no or {}, unsure, []

    def __call__(self, q: Question, material: str) -> tuple[Verdict, bool]:
        self.asked.append(q.id)
        answer = not any(s in material for s in self.no.get(q.id, ()))
        v = Verdict(question_id=q.id, answer=answer, confidence=0.9, confidence_source="self_report", backend="fake",
                    escalated=False, cost_usd=0.0, latency_ms=1, trace_id="t", judge_id="p2.judge")  # fmt: skip
        return v, not any(s in material for s in self.unsure)


def entry(text: str, kind: str, claims=(), premises=(), section_claims=()) -> dict:
    return {"id": "S1", "section": "Findings", "text": text, "kind": kind, "claims": list(claims), "premises": list(premises),
            "section_claims": list(section_claims)}  # fmt: skip


def test_AUD_F_12_a_claim_that_says_more_than_its_quote_fails() -> None:
    ask = Says(no={"claim.within_quote": ("structured form of context engineering",)})
    findings, counts = sentences.audit([entry("The review calls it context engineering [R87].", "claim", ["C3"])], CLAIMS, ask, "x")
    assert [(f.check, f.severity) for f in findings] == [("sentence", "fail")] and "C3 says more than its quote" in findings[0].summary
    assert ask.asked == ["claim.within_quote"] and counts == {"sentences": 1, "claim": 1, "fail": 1}
    warn, _ = sentences.audit([entry("The SWE-agent study warns [R1].", "claim", ["C4"])], CLAIMS, Says(), "x")
    assert warn[0].severity == "warn" and "back-reference" in warn[0].summary  # a quote that leans on context


def test_AUD_F_12_a_synthesis_that_does_not_follow_or_names_one_source_as_two_fails() -> None:
    two = entry("The two studies therefore disagree about length.", "synthesis", premises=["C1", "C2"])
    findings, _ = sentences.audit([two], CLAIMS, Says(), "x")
    assert findings[0].severity == "fail" and "1 source" in findings[0].summary  # both premises are R2
    over = entry("So length always causes failure.", "synthesis", premises=["C1"])
    findings, _ = sentences.audit([over], CLAIMS, Says(no={"paper.inference_follows": ("always causes",)}), "x")
    assert findings[0].severity == "fail" and "does not follow" in findings[0].summary
    unsure, _ = sentences.audit([over], CLAIMS, Says(unsure=("always causes",)), "x")
    assert unsure[0].severity == "warn"
    fine, _ = sentences.audit([entry("Taken together, length tracks failure.", "synthesis", premises=["C1"])], CLAIMS, Says(), "x")
    assert fine == []


def test_AUD_F_12_claim_free_sentences_are_checked_by_rule_and_by_the_judge() -> None:
    rules = [entry("No passage covers recursive language models on cost.", "transition"),
             entry("Context language models were proposed by Shao and colleagues.", "transition")]  # fmt: skip
    ask = Says()
    findings, _ = sentences.audit(rules, CLAIMS, ask, "x")
    assert [f.severity for f in findings] == ["fail", "fail"] and ask.asked == []  # by rule, before any judge
    fact = entry("Most agents fail on long tasks.", "transition")
    findings, _ = sentences.audit([fact], CLAIMS, Says(no={"sentence.no_fact": ("Most agents",)}), "x")
    assert findings[0].severity == "fail" and "transition that states a fact" in findings[0].summary
    assert sentences.audit([entry("We turn next to repair.", "transition")], CLAIMS, Says(), "x")[0] == []


def test_AUD_F_12_a_document_made_before_sentence_status_is_split_and_checked() -> None:
    text = ("Longer runs failed more often [R2]. Failed runs took more steps [R2].\n\nAnother paper, by contrast, finds the "
            "opposite. We turn next to repair. No passage covers cost.")  # fmt: skip
    entries = sentences.from_text([("Findings", text)], ["C1", "C2"])
    assert [(e["kind"], e["claims"]) for e in entries] == [("claim", ["C1"]), ("claim", ["C2"]), ("unrecorded", []),
                                                           ("unrecorded", []), ("unrecorded", [])]  # fmt: skip
    ask = Says(no={"sentence.no_fact": ("by contrast",), "paper.inference_follows": ("by contrast",)})
    findings, counts = sentences.audit(entries, CLAIMS, ask, "paper/paper.json")
    by_text = {f.summary.split(": ", 1)[0]: f for f in findings}
    assert counts["unrecorded"] == 3 and counts["claim"] == 2
    contrast = next(f for f in findings if "by contrast" in f.summary)
    assert contrast.severity == "fail" and "does not follow from its section's claims" in contrast.summary
    assert any("No passage covers" in f.summary and f.severity == "fail" for f in findings)
    assert not any("We turn next" in f.summary for f in findings)
    assert by_text  # every finding names its sentence
    follows = sentences.audit(sentences.from_text([("F", "Runs failed [R2]. So longer runs fail more.")], ["C1"]), CLAIMS,
                              Says(no={"sentence.no_fact": ("So longer",)}), "x")[0]  # fmt: skip
    assert follows[0].severity == "warn" and "without naming its premises" in follows[0].summary


def test_AUD_F_12_the_increment_6_papers_split_into_their_claims() -> None:
    for doc_path in sorted((ROOT / "data" / "paper_demo").glob("*/paper/paper.json")):
        doc = json.loads(doc_path.read_text(encoding="utf-8"))
        evidence = [(s["heading"], s["text"]) for s in doc["sections"] if s["kind"] == "evidence"]
        entries = sentences.from_text(evidence, [c["id"] for c in doc["claims"]])
        claimed = [c for e in entries for c in e["claims"]]
        assert claimed == [c["id"] for c in doc["claims"]], doc_path  # every claim lands on its sentence, in order
        assert sum(e["kind"] == "unrecorded" for e in entries) >= 20


def test_AUD_F_12_the_paper_audit_runs_on_new_and_old_papers(tmp_path: Path, monkeypatch) -> None:
    from tests.test_paper_interpret import InterpretJudge  # noqa: PLC0415

    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    out = deps.run_dir / "paper"
    assert pipeline.run_paper_audit(deps, judge=InterpretJudge()) == "green"
    assert "Sentences re-checked:" in (out / "audit.md").read_text("utf-8")
    doc = json.loads((out / "paper.json").read_text("utf-8"))
    assert doc["sentences"]
    doc["sentences"] = []  # as a paper made before 0.13 is stored
    (out / "paper.json").write_text(json.dumps(doc), encoding="utf-8")
    assert pipeline.run_paper_audit(deps, judge=InterpretJudge()) in ("green", "amber")
    report = json.loads((out / "audit_report.json").read_text("utf-8"))
    assert "sentence" in report["checks_run"]


def test_AUD_F_12_the_review_audit_re_checks_its_sentences(tmp_path: Path, monkeypatch) -> None:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    review = (deps.run_dir / "literature.md").read_text("utf-8")
    (deps.run_dir / "literature.md").write_text(review.replace("A review [R1].", "A review [R1]. Shao and colleagues agree."), "utf-8")
    (deps.run_dir / "claims.jsonl").write_text("", encoding="utf-8")
    light = pipeline.run_audit(deps, judge=LitJudge())
    report = json.loads((deps.run_dir / "artifacts" / "audit_report.json").read_text("utf-8"))
    assert "sentence" in report["checks_run"] and light == "red"
    assert any(f["check"] == "sentence" and "Shao and colleagues" in f["summary"] for f in report["findings"])


def test_AUD_F_12_the_pdf_says_what_green_covers_and_lists_synthesis_and_repeats() -> None:
    pymupdf = pytest.importorskip("pymupdf")
    paper = {"markdown": "## Findings\n\nLonger runs failed [R2]. Taken together, length tracks failure.\n",
             "claims": [{"id": "C1", **CLAIMS["C1"], "locator": "sec. 3"}, {"id": "C2", **CLAIMS["C1"], "same_quote_as": "C1"}],
             "sources": {"R2": {"title": "Trajectory failures"}}, "audit_markdown": None,
             "audit": {"overall": "green", "checks_run": ["citation", "claim_support", "sentence"], "findings": []},
             "sentences": [{"id": "S2", "section": "Findings", "text": "Taken together, length tracks failure.", "kind": "synthesis",
                            "premises": ["C1"], "claims": [], "status": "pass"},
                           {"id": "S3", "section": "Findings", "text": "No passage covers cost.", "kind": "transition",
                            "premises": [], "claims": [], "status": "removed", "reason": "absence"}]}  # fmt: skip
    pdf = render_pdf(paper, {"title": "T", "kind": "literature", "date": "2026-10-13", "spent_usd": 0.2, "cap_usd": 1.0, "run_id": "r"})
    text = " ".join(" ".join(p.get_text() for p in pymupdf.open(stream=pdf, filetype="pdf")).split())
    for expected in ("says no more than the passage it quotes", "the other sentences state no facts", "model cost of this run",
                     "Synthesis sentences", "rests on C1", "removed: absence", "The same quote as C1"):  # fmt: skip
        assert expected in text, expected
