# ruff: noqa: E501
"""AUD-F-13: when the audit's judge contradicts the verdict recorded at write time, the audit says the judges disagree
(a warning), not that the sentence failed. No network: fake judges."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge
from tests.test_paper_evidence import make_review
from tests.test_paper_pipeline import finish_review, make_deps, script
from vera.app import pipeline
from vera.app.pdf import render_pdf
from vera.audit import disagreement
from vera.schemas import Evidence, Finding, PaperRequest, Verdict


def verdict(qid: str, answer: bool, confidence: float = 0.9, backend: str = "glm-flash") -> Verdict:
    return Verdict(question_id=qid, answer=answer, confidence=confidence, confidence_source="self_report", backend=backend,
                   escalated=False, cost_usd=0.0, latency_ms=1, trace_id="t", judge_id="p2.judge")  # fmt: skip


def finding(key: str, verdicts: list[Verdict], check: str = "sentence", severity: str = "fail") -> Finding:
    return Finding(check=check, severity=severity, claim_ids=["C1"], verdicts=verdicts, summary=f"{key}: C1 says more than its quote",
                   evidence=[Evidence(claim_id=key, source="log", reference="paper/paper.json", matched=False, detail="x")])  # fmt: skip


def record(sid: str, verdicts: list[Verdict]) -> dict:
    return {"id": sid, "verdicts": [v.model_dump(mode="json") for v in verdicts]}


def test_AUD_F_13_a_write_time_yes_and_an_audit_no_is_a_disagreement_not_a_failure() -> None:
    audit_no = verdict("claim.within_quote", False, 0.98, "glm-flash")
    written_yes = [verdict("lit.claim_supported", True), verdict("claim.within_quote", True, 0.71, "jev")]
    out, n = disagreement.reconcile([finding("S76", [audit_no])], [record("S76", written_yes)], [])
    assert n == 1 and out[0].severity == "warn"
    assert out[0].summary.startswith("judges disagree (passed at write time, yes on jev at 0.71; failed in the audit, no on glm-flash at 0.98)")


@pytest.mark.parametrize(
    "written, audit_v, why",
    [
        ([verdict("claim.within_quote", True), verdict("claim.within_quote", False)], verdict("claim.within_quote", False), "the last write-time verdict was a no"),
        ([verdict("claim.within_quote", True, 0.6)], verdict("claim.within_quote", False), "the write-time yes was not confident"),
        ([verdict("claim.within_quote", True)], verdict("claim.within_quote", False, 0.6), "the audit's no was not confident"),
        ([verdict("lit.claim_supported", True)], verdict("claim.within_quote", False), "no write-time verdict on the same question"),
        ([], verdict("claim.within_quote", False), "a document made before sentence statuses has none"),
    ],
)
def test_AUD_F_13_a_failure_stays_a_failure_otherwise(written: list, audit_v: Verdict, why: str) -> None:
    out, n = disagreement.reconcile([finding("S2", [audit_v])], [record("S2", written)] if written else [], [])
    assert n == 0 and out[0].severity == "fail", why


def test_AUD_F_13_a_rule_failure_and_other_checks_are_left_alone() -> None:
    rule = finding("S3", [])  # a rule, not a judge: no verdict
    cite = finding("S4", [verdict("claim.within_quote", False)], check="citation")
    out, n = disagreement.reconcile([rule, cite], [record("S3", [verdict("claim.within_quote", True)])], [])
    assert n == 0 and [f.severity for f in out] == ["fail", "fail"]


def test_AUD_F_13_statements_keep_their_write_time_verdicts_and_disagree_like_sentences(tmp_path: Path, monkeypatch) -> None:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    doc = json.loads((deps.run_dir / "paper" / "paper.json").read_text("utf-8"))
    kept = [i for i in doc["inferences"] if i["status"] == "pass"]
    assert kept and all(i["verdicts"] for i in kept)  # Increment 8: the interpretation stage stores them
    assert {v["question_id"] for i in kept for v in i["verdicts"]} == {"paper.inference_follows"}

    class AuditSaysNo(LitJudge):  # the audit's judge says no to every within-quote and inference question
        def ask(self, state, questions):
            out = super().ask(state, questions)
            return [v.model_copy(update={"answer": False}) if v.question_id in ("claim.within_quote", "paper.inference_follows") else v
                    for v in out]  # fmt: skip

    light = pipeline.run_paper_audit(deps, judge=AuditSaysNo())
    report = json.loads((deps.run_dir / "paper" / "audit_report.json").read_text("utf-8"))
    disagree = [f for f in report["findings"] if f["summary"].startswith("judges disagree")]
    fails = [f for f in report["findings"] if f["severity"] == "fail"]
    assert disagree and not fails and light == "amber"  # every no contradicts a confident write-time yes
    assert {f["check"] for f in disagree} == {"sentence", "inference"}
    assert "Judge disagreements:" in (deps.run_dir / "paper" / "audit.md").read_text("utf-8")


def test_AUD_F_13_the_pdf_lists_disagreements_apart() -> None:
    pymupdf = pytest.importorskip("pymupdf")
    findings = [{"severity": "warn", "check": "sentence", "summary": "judges disagree (passed at write time, yes on jev at 0.71; failed in the audit, no on glm-flash at 0.98): S76"},
                {"severity": "warn", "check": "sentence", "summary": "S9: judge unsure"}]  # fmt: skip
    paper = {"markdown": "## Findings\n\nText.\n", "claims": [], "sources": {}, "audit_markdown": None,
             "audit": {"overall": "amber", "checks_run": ["citation", "sentence"], "findings": findings}}  # fmt: skip
    pdf = render_pdf(paper, {"title": "T", "kind": "literature", "date": "2026-10-14", "run_id": "r"})
    text = " ".join(" ".join(p.get_text() for p in pymupdf.open(stream=pdf, filetype="pdf")).split())
    assert "Judge disagreements (1)" in text and "a warning can be a judge disagreement" in text and "S9: judge unsure" in text
