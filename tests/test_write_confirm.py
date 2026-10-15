# ruff: noqa: E501
"""RSH-F-17: while writing, a cheap judge's confident "no" on a question the audit confirms is put to the reference judge
before the sentence or statement is repaired or removed. Fake judges, no network."""

from __future__ import annotations

import json
from pathlib import Path

from tests.lit_fakes import LitJudge
from tests.test_paper_evidence import make_review
from tests.test_paper_pipeline import finish_review, make_deps, script
from tests.test_routes import Fake
from tests.test_sentence_checks import C_LONG, C_REV, deps_for, loose, outcome, verify
from vera.app import pipeline
from vera.literature import confirm
from vera.schemas import PaperRequest

GPT = {"text": "The trajectory study ran GPT-3.5-turbo agents whose longer runs failed.", "claim": {**C_LONG["claim"]}, "ref": "s1"}


def with_reference(deps, answer: bool, confidence: float = 0.9) -> Fake:
    deps.extra["reference"] = ref = Fake("sonnet-ref", answer=answer, confidence=confidence)
    return ref


def test_RSH_F_17_a_cheap_no_the_reference_overrules_is_kept_without_repair(tmp_path: Path) -> None:
    deps = deps_for(tmp_path, [[None]], no={"claim.within_quote": ("GPT-3.5",)})
    ref = with_reference(deps, answer=True)
    checked = verify(deps, [[GPT, C_REV]])
    assert outcome(checked, "s1")["status"] == "pass" and outcome(checked, "s1")["reason"] is None
    assert deps.generator.calls == []  # no repair call
    assert ref.asked == ["claim.within_quote"]
    assert [v.backend for v in outcome(checked, "s1")["verdicts"]][-1] == "sonnet-ref"


def test_RSH_F_17_a_cheap_no_the_reference_confirms_is_repaired_and_rechecked(tmp_path: Path) -> None:
    fixed = {"text": "The trajectory study links longer trajectories to failure.", "claim": {**C_LONG["claim"]}}
    deps = deps_for(tmp_path, [[fixed]], no={"claim.within_quote": ("GPT-3.5",)})
    with_reference(deps, answer=False)
    checked = verify(deps, [[GPT, C_REV]])
    assert outcome(checked, "s1")["status"] == "pass" and outcome(checked, "s1")["text"] == fixed["text"]
    assert deps.generator.calls == ["p3.synthesize"]  # one repair call
    assert checked.reasons == {"says more than its quote": 1}


def test_RSH_F_17_an_unsure_reference_keeps_the_sentence_as_unsettled(tmp_path: Path) -> None:
    deps = deps_for(tmp_path, [[None]], no={"claim.within_quote": ("GPT-3.5",)})
    with_reference(deps, answer=False, confidence=0.6)
    checked = verify(deps, [[GPT, C_REV]])
    assert outcome(checked, "s1")["status"] == "pass" and outcome(checked, "s1")["reason"] == confirm.UNSETTLED_AT_WRITE
    assert deps.generator.calls == []


def test_RSH_F_17_without_a_reference_the_write_step_is_as_before(tmp_path: Path) -> None:
    deps = deps_for(tmp_path, [[None]], no={"claim.within_quote": ("GPT-3.5",)})
    checked = verify(deps, [[GPT, C_REV]])
    assert outcome(checked, "s1")["status"] == "removed" and checked.reasons == {"says more than its quote": 1}


def test_RSH_F_17_a_synthesis_the_reference_accepts_is_kept(tmp_path: Path) -> None:
    syn = loose("Taken together, trajectory length tracks failure.", "s4", "synthesis", ("s1",))
    deps = deps_for(tmp_path, [[None]], no={"paper.inference_follows": ("tracks failure",)})
    ref = with_reference(deps, answer=True)
    checked = verify(deps, [[C_LONG, C_REV, syn]])
    assert outcome(checked, "s4")["status"] == "pass" and ref.asked == ["paper.inference_follows"]
    assert deps.generator.calls == []


def test_RSH_F_17_the_paper_and_its_statements_use_it_and_the_writer_never_judges(tmp_path: Path, monkeypatch) -> None:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    deps.judge = LitJudge(deps.ledger, deps.budget, answers={"paper.inference_follows": False})
    ref = with_reference(deps, answer=True)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    doc = json.loads((deps.run_dir / "paper" / "paper.json").read_text("utf-8"))
    kept = [i for i in doc["inferences"] if i["status"] == "pass"]
    assert kept and all(i["verdicts"][-1]["backend"] == "sonnet-ref" for i in kept)
    assert "paper.inference_follows" in ref.asked
    producers = {"p3.paper.write", "p3.paper.interpret", "p3.synthesize"}
    judges = {v["judge_id"] for i in doc["inferences"] for v in i["verdicts"]}
    assert not judges & producers
