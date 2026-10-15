# ruff: noqa: E501
"""RSH-F-17 (completed, Increment 10): the audit keeps the reference's write-time answer on unchanged text instead of asking
again. Fake judges, no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge
from tests.test_paper_evidence import make_review
from tests.test_paper_pipeline import finish_review, make_deps, script
from tests.test_routes import Fake
from vera.app import pipeline
from vera.audit import sticky
from vera.literature import sentence_checks
from vera.schemas import PaperRequest

ROOT = Path(__file__).resolve().parents[1]


class InferenceNo(LitJudge):
    def ask(self, state, questions):
        return [v.model_copy(update={"answer": False}) if v.question_id == "paper.inference_follows" else v
                for v in super().ask(state, questions)]  # fmt: skip


def made(tmp_path: Path, monkeypatch, write_answer: bool, write_conf: float = 0.9):
    """A paper whose statements the cheap judge rejected at write time and the reference answered (stored)."""
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    deps.judge = InferenceNo(deps.ledger, deps.budget)
    deps.extra["reference"] = Fake("sonnet-ref", answer=write_answer, confidence=write_conf)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    return deps


def audit(deps, reference):
    pipeline.run_paper_audit(deps, judge=InferenceNo(), reference=reference)
    return json.loads((deps.run_dir / "paper" / "audit_report.json").read_text("utf-8"))


def test_RSH_F_17_a_stored_confident_yes_is_kept_and_the_reference_is_not_asked_again(tmp_path: Path, monkeypatch) -> None:
    deps = made(tmp_path, monkeypatch, write_answer=True)
    again = Fake("sonnet-ref", answer=False)
    report = audit(deps, again)
    assert "paper.inference_follows" not in again.asked
    statements = [f for f in report["findings"] if f["check"] == "inference"]
    assert statements and all(f["summary"].startswith("judges disagree") for f in statements)


def test_RSH_F_17_a_stored_unsure_answer_is_kept_and_the_item_is_unsettled(tmp_path: Path, monkeypatch) -> None:
    deps = made(tmp_path, monkeypatch, write_answer=False, write_conf=0.62)
    again = Fake("sonnet-ref", answer=False, confidence=0.95)
    report = audit(deps, again)
    assert "paper.inference_follows" not in again.asked
    statements = [f for f in report["findings"] if f["check"] == "inference"]
    assert statements and all(f["severity"] == "warn" and f["summary"].startswith("unsettled") for f in statements)


def test_RSH_F_17_changed_text_is_confirmed_afresh(tmp_path: Path, monkeypatch) -> None:
    deps = made(tmp_path, monkeypatch, write_answer=True)
    path = deps.run_dir / "paper" / "paper.json"
    doc = json.loads(path.read_text("utf-8"))
    for i in doc["inferences"]:
        i["text"] = i["text"] + " Edited later."  # the stored answers no longer match the text the audit reads
    path.write_text(json.dumps(doc), encoding="utf-8")
    stored = sticky.index(doc["inferences"])
    claims = {"C1": "a claim (source: x)"}
    _, material = sentence_checks.follows_strict("The sources leave much open.", ["C1"], claims)
    assert sticky.lookup(stored, "paper.inference_follows", material) is None


def test_RSH_F_17_the_item_text_is_read_back_from_the_judges_material() -> None:
    _, m1 = sentence_checks.within_quote("The study finds X (with a bracket).", "the quote says X", "A title")
    assert sticky.item_text("claim.within_quote", m1) == "The study finds X (with a bracket)."
    _, m2 = sentence_checks.follows_strict("Traces may help (C1, C2).", ["C1", "C2"], {"C1": "a", "C2": "b"})
    assert sticky.item_text("paper.inference_follows", m2) == "Traces may help."
    assert sticky.item_text("sentence.no_fact", "Sentence: x") is None


def test_RSH_F_17_the_offline_reread_of_the_increment_9_papers_is_recorded() -> None:
    path = ROOT / "data" / "results" / "sticky10.json"
    if not path.exists():
        pytest.skip("scripts/reread10.py has not been run")
    result = json.loads(path.read_text(encoding="utf-8"))["papers"]
    assert result["N1"]["after"]["fails"] == 0 and [m["item"] for m in result["N1"]["moved"]] == ["S61"]
    assert result["N2"]["after"]["fails"] == 2 and result["N2"]["moved"] == []  # the blind spot is not this fix's to close
