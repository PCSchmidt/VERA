"""v0.2 schemas (docs/03): JSON round-trips, no self-grading, hard budgets."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from vera.schemas import (
    SCHEMA_VERSION,
    AuditReport,
    Budget,
    BudgetExceeded,
    Claim,
    Evidence,
    Finding,
    LedgerRecord,
    Location,
    Question,
    QuestionType,
    RoutingPolicy,
    SelfGradingError,
    StageResult,
    Verdict,
)


def verdict(**overrides: object) -> Verdict:
    fields: dict[str, object] = {
        "question_id": "aud.cite.exists",
        "answer": True,
        "probabilities": {"true": 0.93, "false": 0.07},
        "confidence": 0.93,
        "backend": "cheap-local",
        "escalated": False,
        "cost_usd": 0.0001,
        "latency_ms": 412,
        "trace_id": "t-1",
        "producer_id": "p1.claim_extractor",
        "judge_id": "p2.router",
    }
    fields.update(overrides)
    return Verdict(**fields)


def budget() -> Budget:
    return Budget(max_usd=1.0, max_wall_seconds=900, max_model_calls=10)


SAMPLES: list[BaseModel] = [
    Question(id="aud.cite.exists", type=QuestionType.BOOLEAN, text="Does reference 12 exist?"),
    Question(
        id="aud.num.agree", type=QuestionType.CHOICE, text="Do text and table agree?", options=["yes", "no", "unclear"]
    ),
    Question(
        id="jdg.quality", type=QuestionType.SCORE, text="Rate grounding", scale=(1, 5), rubric="5 = fully grounded"
    ),
    verdict(),
    verdict(answer=4, probabilities=None, producer_id=None),
    verdict(answer="no"),
    RoutingPolicy(per_question={"aud.cite.exists": 0.8}),
    LedgerRecord(
        trace_id="t-1", run_id="r-1", component="p2.router", backend="openrouter", model="z-ai/glm-5.3-flash",
        input_tokens=812, output_tokens=40, cost_usd=0.00015, latency_ms=640, timestamp="2026-09-29T14:00:00Z",
    ),
    LedgerRecord(
        trace_id="t-2", run_id="r-1", component="p1.cite_check", backend="local", model="rules",
        input_tokens=None, output_tokens=None, cost_usd=0.0, latency_ms=3, timestamp="2026-09-29T14:00:01Z",
    ),
    budget(),
    Location(page=4, section="4.2", table="Table 3", quote="improves by 3.1%"),
    Claim(id="c1", kind="numeric", text="improves accuracy by 3.1%", value=3.1, location=Location(page=4)),
    Evidence(claim_id="c1", source="paper", reference="Table 3, row 2", matched=False, detail="table says 2.4%"),
    Finding(
        check="numeric", severity="fail", claim_ids=["c1"],
        evidence=[Evidence(claim_id="c1", source="paper", reference="Table 3", matched=False)],
        verdicts=[verdict()], summary="Text and Table 3 disagree",
    ),
    AuditReport(
        paper_id="st-001", paper_source="https://scientist-two.github.io/", repo=None, findings=[],
        overall="green", checks_run=["citation"], checks_skipped={"rerun": "no code"}, total_cost_usd=0.02,
        wall_seconds=95,
    ),
    StageResult(
        run_id="r-1", stage="baseline", artifact_ref="runs/r-1/baseline.json", producer_id="p3.runner",
        gate=verdict(producer_id="p3.runner", judge_id="p2.router"), decision="accept",
        metrics={"accuracy": 0.81}, budget_after=budget(),
    ),
]


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_model_round_trips_through_json(model: BaseModel) -> None:
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model


def test_every_schema_model_has_a_round_trip_sample() -> None:
    covered = {type(m) for m in SAMPLES}
    expected = {Question, Verdict, RoutingPolicy, LedgerRecord, Budget, Location, Claim, Evidence,
                Finding, AuditReport, StageResult}
    assert expected <= covered


def test_verdict_answer_types_survive_round_trip() -> None:
    for answer in (True, 4, "no"):
        restored = Verdict.model_validate_json(verdict(answer=answer).model_dump_json())
        assert restored.answer == answer and type(restored.answer) is type(answer)


def test_verdict_rejects_self_grading() -> None:
    with pytest.raises(ValidationError) as exc:
        verdict(producer_id="p2.router", judge_id="p2.router")
    assert "grade its own work" in str(exc.value)
    assert issubclass(SelfGradingError, ValueError)


def test_verdict_rejects_self_grading_on_deserialize() -> None:
    raw = verdict().model_dump()
    raw["producer_id"] = raw["judge_id"]
    with pytest.raises(ValidationError):
        Verdict.model_validate(raw)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_verdict_confidence_bounded(confidence: float) -> None:
    with pytest.raises(ValidationError):
        verdict(confidence=confidence)


def test_audit_report_carries_current_schema_version() -> None:
    report = next(m for m in SAMPLES if isinstance(m, AuditReport))
    assert report.schema_version == SCHEMA_VERSION


def test_budget_charge_accumulates() -> None:
    b = budget()
    b.charge(0.25, seconds=30)
    b.charge(0.25, seconds=30, calls=2)
    assert (b.spent_usd, b.elapsed_seconds, b.model_calls_used) == (0.5, 60, 3)


@pytest.mark.parametrize(
    ("usd", "seconds", "calls", "limit"),
    [(1.01, 0, 1, "usd"), (0.1, 901, 1, "wall"), (0.1, 0, 11, "calls")],
)
def test_budget_raises_on_each_limit_without_partial_charge(usd: float, seconds: int, calls: int, limit: str) -> None:
    b = budget()
    with pytest.raises(BudgetExceeded, match=limit):
        b.charge(usd, seconds=seconds, calls=calls)
    assert (b.spent_usd, b.elapsed_seconds, b.model_calls_used) == (0.0, 0, 0)


def test_budget_allows_exactly_reaching_limit() -> None:
    b = budget()
    b.charge(1.0, seconds=900, calls=10)
    with pytest.raises(BudgetExceeded):
        b.charge(0.0, seconds=0, calls=1)


def test_budget_without_call_limit_ignores_calls() -> None:
    b = Budget(max_usd=1.0, max_wall_seconds=60)
    b.charge(0.1, calls=1000)
    assert b.model_calls_used == 1000


def test_budget_rejects_negative_charges() -> None:
    with pytest.raises(ValueError):
        budget().charge(-0.1)
