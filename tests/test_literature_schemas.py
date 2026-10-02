"""v0.9 schemas (docs/03): the literature stage's types and the multi-verdict StageResult."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from tests.test_loop_stages import FakeSandbox, ds, make_deps, run_loop
from tests.test_schemas import budget, verdict
from vera.schemas import (
    SCHEMA_VERSION,
    ClaimLink,
    LiteratureSection,
    RunSpec,
    ScopedQuestion,
    SelfGradingError,
    SourceRecord,
    StageResult,
    Topic,
)


def source(key: str = "R1") -> SourceRecord:
    return SourceRecord(key=key, id="arXiv:2510.24815", title="TreeHFD", source="arxiv", url="https://arxiv.org/abs/x")


def scoped(**overrides: object) -> ScopedQuestion:
    fields: dict[str, object] = {"topic_id": "t-a", "question": "Does X hold?", "why_researchable": "small data",
                                 "empirical": True}  # fmt: skip
    return ScopedQuestion(**(fields | overrides))


SAMPLES: list[BaseModel] = [
    Topic(id="t-a", text="explainability of tree ensembles", key_papers_ref="data/topics/t-a.json"),
    scoped(),
    scoped(status="confirmed", confirmed_by="Chris", confirmed_at="2026-10-03T09:00:00Z"),
    source(),
    ClaimLink(claim="C", source_key="R1", quote="a verbatim span", locator="abstract", quote_check="pass",
              verdicts=[verdict(question_id="lit.claim_supported", producer_id="p3.synthesize")]),  # fmt: skip
    LiteratureSection(run_id="r-1", topic_id="t-a", text="X [R1].",
                      claims=[ClaimLink(claim="X", source_key="R1", quote="q", locator="abstract")],
                      sources=[source()]),  # fmt: skip
]


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_literature_model_round_trips_through_json(model: BaseModel) -> None:
    assert type(model).model_validate_json(model.model_dump_json()) == model


def test_schema_version_is_0_9() -> None:
    assert SCHEMA_VERSION == "0.9"


def test_a_confirmed_question_needs_who_and_when() -> None:
    with pytest.raises(ValidationError):
        scoped(status="confirmed")
    with pytest.raises(ValidationError):
        scoped(status="edited", confirmed_by="Chris")
    with pytest.raises(ValidationError):
        scoped(confirmed_by="Chris", confirmed_at="2026-10-03T09:00:00Z")  # proposed, yet confirmed


def test_a_non_empirical_question_has_no_parent() -> None:
    with pytest.raises(ValidationError):
        scoped(empirical=False, candidate_parent="2510.24815")


@pytest.mark.parametrize("quote", ["", "   "])
def test_a_claim_without_a_quote_is_rejected(quote: str) -> None:
    with pytest.raises(ValidationError):
        ClaimLink(claim="C", source_key="R1", quote=quote, locator="abstract")


def test_a_claim_citing_an_unretrieved_source_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        LiteratureSection(run_id="r", topic_id="t", text="x", sources=[source("R1")],
                          claims=[ClaimLink(claim="x", source_key="R9", quote="q", locator="abstract")])  # fmt: skip
    assert "not retrieved" in str(exc.value)


def test_a_topic_needs_a_safe_id_and_text() -> None:
    with pytest.raises(ValidationError):
        Topic(id="../x", text="t")
    with pytest.raises(ValidationError):
        Topic(id="ok", text="  ")


def stage(**overrides: object) -> StageResult:
    fields: dict[str, object] = {
        "run_id": "r-1", "stage": "subset_exp", "artifact_ref": "a.json", "producer_id": "p3.runner",
        "gates": [verdict(producer_id="p3.runner", judge_id="p2.router")], "decision": "accept",
        "budget_after": budget(),
    }  # fmt: skip
    return StageResult(**(fields | overrides))


def test_a_stage_without_a_verdict_is_rejected() -> None:
    with pytest.raises(ValidationError):
        stage(gates=[])


def test_a_reject_must_name_its_verdict_or_its_reason() -> None:
    with pytest.raises(ValidationError) as exc:
        stage(decision="reject")
    assert "must name" in str(exc.value)
    rejected = stage(decision="reject", deciding_gates=[0])
    assert rejected.gate == rejected.gates[0]
    assert stage(decision="reject", reason="the report is too long").reason


def test_deciding_gates_must_exist() -> None:
    with pytest.raises(ValidationError):
        stage(decision="reject", deciding_gates=[3])


def test_every_verdict_in_the_list_is_checked_for_self_grading() -> None:
    ok = verdict(producer_id="p3.runner", judge_id="p2.router")
    bad = verdict(producer_id=None, judge_id="p3.runner")
    with pytest.raises(ValidationError) as exc:
        stage(gates=[ok, bad])
    assert "its own producer" in str(exc.value)
    assert issubclass(SelfGradingError, ValueError)


def test_a_stage_stored_with_one_gate_still_loads() -> None:
    raw = stage(decision="reject", deciding_gates=[0]).model_dump(mode="json")
    dropped = ("gates", "deciding_gates", "reason")
    legacy = {k: v for k, v in raw.items() if k not in dropped} | {"gate": raw["gates"][0]}
    loaded = StageResult.model_validate(legacy)
    assert loaded.gates == stage(decision="reject", deciding_gates=[0]).gates and loaded.deciding_gates == [0]


def test_run_spec_accepts_a_topic() -> None:
    assert RunSpec.model_fields["topic"].annotation is not None


def test_RSH_F_02_a_rejected_experiments_stage_shows_the_verdicts_that_rejected_it(tmp_path: Path) -> None:
    ideas = {"C1": {"analytical": ds(2.6), "airfoil": ds(3.0)}, "C2": {"analytical": ds(2.9), "airfoil": ds(2.6)}}
    state = run_loop(make_deps(tmp_path, sandbox=FakeSandbox(ideas=ideas)))
    sr = next(StageResult.model_validate(s) for s in state["stage_results"] if s["stage"] == "subset_exp")
    assert sr.decision == "reject" and sr.deciding_gates
    assert len(sr.gates) == 4  # 2 ideas x 2 datasets, all asked and kept
    assert all(sr.gates[i].answer is not True for i in sr.deciding_gates)
    assert sr.gate.answer is not True  # the stage no longer reports a "yes" for a rejected stage
