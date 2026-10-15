# ruff: noqa: E501
"""AUD-F-14: a failure needs a confident no from the judge of record; an unsure answer, either way, is "unsettled"."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_disagreement import finding, record, verdict
from tests.test_routes import Fake, SaysNo, audited
from vera.app.pdf import render_pdf
from vera.audit import disagreement

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "ref, before, expected",
    [
        (verdict("claim.within_quote", False, 0.93, "sonnet-ref"), None, "fail"),  # a confident reference no
        (verdict("claim.within_quote", False, 0.62, "sonnet-ref"), None, "unsettled"),  # an unsure reference no
        (verdict("claim.within_quote", True, 0.68, "sonnet-ref"), None, "unsettled"),  # an unsure reference yes
        (verdict("claim.within_quote", True, 0.88, "sonnet-ref"), None, "disagree"),  # a confident reference yes
        (None, verdict("claim.within_quote", True, 0.9, "jev"), "disagree"),  # no reference; a confident write-time yes
        (None, verdict("claim.within_quote", True, 0.88, "sonnet-ref"), "disagree"),  # the reference's yes, stored at write time
        (None, None, "fail"),  # the cheap judge's confident no, nothing against it
    ],
)
def test_AUD_F_14_the_judge_of_record_decides_and_unsure_is_unsettled(ref, before, expected) -> None:
    audit_no = verdict("claim.within_quote", False, 0.98, "glm-flash")
    kind, why = disagreement.outcome(audit_no, ref, before)
    assert kind == expected
    if kind == "unsettled":
        assert "unsure" in why and f"{ref.confidence:.2f}" in why


def test_AUD_F_14_an_unsure_reference_makes_a_warning_and_a_rule_failure_stays() -> None:
    audit_no = verdict("claim.within_quote", False, 0.9, "jev")
    unsure = verdict("claim.within_quote", False, 0.62, "sonnet-ref")
    rule = finding("S9", [])
    out, n = disagreement.reconcile([finding("S4", [audit_no]), rule], [record("S4", [])], [], {audit_no.trace_id: unsure})
    assert [f.severity for f in out] == ["warn", "fail"] and n == 0
    assert out[0].summary.startswith("unsettled (the reference judge was unsure (no on sonnet-ref at 0.62")
    assert out[0].verdicts[-1].backend == "sonnet-ref" and disagreement.count_unsettled(out) == 1


def test_AUD_F_14_an_unsure_reference_turns_a_paper_amber_not_red(tmp_path: Path, monkeypatch) -> None:
    out = audited(tmp_path, monkeypatch, SaysNo(), Fake("sonnet-ref", answer=False, confidence=0.6))
    within = [f for f in out["findings"] if "says more than its quote" in f["summary"]]
    assert within and all(f["severity"] == "warn" and f["summary"].startswith("unsettled") for f in within)
    assert out["light"] == "amber"


def test_AUD_F_14_the_pdf_lists_unsettled_items_apart() -> None:
    pymupdf = pytest.importorskip("pymupdf")
    findings = [{"severity": "warn", "check": "sentence", "summary": "unsettled (the reference judge was unsure (no on sonnet-ref at 0.62)): S4"}]
    paper = {"markdown": "## Findings\n\nText.\n", "claims": [], "sources": {}, "audit_markdown": None,
             "audit": {"overall": "amber", "checks_run": ["citation", "sentence"], "findings": findings}}  # fmt: skip
    pdf = render_pdf(paper, {"title": "T", "kind": "literature", "date": "2026-10-14", "run_id": "r"})
    text = " ".join(" ".join(p.get_text() for p in pymupdf.open(stream=pdf, filetype="pdf")).split())
    assert "Unsettled (1)" in text and "an unsettled item on which the reference judge was unsure" in text


def test_AUD_F_14_the_reread_of_increment_8s_reaudits_is_reproducible() -> None:
    stored = ROOT / "data" / "results" / "reread9.json"
    if not stored.exists():
        pytest.skip("scripts/reread9.py has not been run")
    sys.path.insert(0, str(ROOT / "scripts"))
    import reread9  # noqa: PLC0415

    result = json.loads(stored.read_text(encoding="utf-8"))
    for label in reread9.PAPERS:
        report = json.loads((ROOT / "data" / "reaudit8" / label / "audit_report.json").read_text(encoding="utf-8"))
        after, _ = reread9.reread(report["findings"])
        assert reread9.tally(after) == result["papers"][label]["after"]
        assert [f.get("verdicts") for f in after] == [f.get("verdicts") for f in report["findings"]]  # severities only
    assert sum(p["after"]["unsettled"] for p in result["papers"].values()) == 20


def test_AUD_F_14_outcome_takes_stored_dumps_too() -> None:
    cheap = SimpleNamespace(question_id="claim.within_quote", answer=False, confidence=0.98, backend="glm-flash")
    ref = SimpleNamespace(question_id="claim.within_quote", answer=False, confidence=0.93, backend="sonnet-ref")
    assert disagreement.outcome(cheap, ref, None) == ("fail", None)
