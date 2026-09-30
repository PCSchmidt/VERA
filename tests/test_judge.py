"""JDG-F-01: prompts, parsing and verdicts for Boolean, Choice and Score questions. No network."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vera.judge import MALFORMED, build_messages, parse_answer, to_verdict
from vera.schemas import Question, QuestionType, Verdict

BOOL = Question(id="loop.beats_baseline", type=QuestionType.BOOLEAN, text="Does run B beat the baseline?")
CHOICE = Question(id="loop.best", type=QuestionType.CHOICE, text="Which run is best?", options=["A", "B", "C"])
SCORE = Question(id="aud.clarity", type=QuestionType.SCORE, text="How clear is it?", scale=(1, 5), rubric="5 = clear")


def test_JDG_F_01_prompt_states_the_answer_format_per_type() -> None:
    assert "true or false" in build_messages("s", BOOL)[1]["content"]
    assert '["A", "B", "C"]' in build_messages("s", CHOICE)[1]["content"]
    user = build_messages("table here", SCORE)[1]["content"]
    assert "integer from 1 to 5" in user and "Rubric: 5 = clear" in user and "table here" in user


@pytest.mark.parametrize(
    ("question", "reply", "answer", "confidence"),
    [
        (BOOL, '{"answer": true, "probability": 0.9}', True, 0.9),
        (BOOL, 'Sure. {"answer": "False", "probability": 0.8} done', False, 0.8),
        (CHOICE, '{"answer": "b", "probability": 0.6}', "B", 0.6),
        (SCORE, '{"answer": 4, "probability": 0.7}', 4, 0.7),
        (SCORE, '{"answer": "2", "probability": 1}', 2, 1.0),
    ],
)
def test_JDG_F_01_parses_valid_answers_with_self_reported_confidence(
    question: Question, reply: str, answer: object, confidence: float
) -> None:
    parsed = parse_answer(question, reply)
    assert (parsed.answer, parsed.confidence, parsed.source) == (answer, confidence, "self_report")


@pytest.mark.parametrize(
    ("question", "reply"),
    [
        (BOOL, "yes"),  # no JSON
        (BOOL, '{"answer": "maybe", "probability": 0.9}'),
        (CHOICE, '{"answer": "D", "probability": 0.9}'),  # not an option
        (SCORE, '{"answer": 6, "probability": 0.9}'),  # out of scale
        (SCORE, '{"answer": 2.5, "probability": 0.9}'),
        (SCORE, '{"answer": true, "probability": 0.9}'),  # a bool is not a score
        (BOOL, '{"answer": true, "probability": 1.7}'),  # probability out of range
        (BOOL, '{"answer": true}'),  # no confidence
        (BOOL, "{not json}"),
    ],
)
def test_JDG_F_01_malformed_or_unusable_replies_get_zero_confidence(question: Question, reply: str) -> None:
    parsed = parse_answer(question, reply)
    assert parsed.confidence == 0.0 and parsed.source == "none"
    if "answer" not in reply or "maybe" in reply or "D" in reply or "6" in reply or "2.5" in reply:
        assert parsed.answer == MALFORMED


def test_JDG_F_01_logprobs_take_precedence_and_are_normalised() -> None:
    parsed = parse_answer(BOOL, '{"answer": true, "probability": 0.99}', answer_probs={"true": 0.6, "false": 0.2})
    assert parsed.source == "logprobs"
    assert parsed.confidence == pytest.approx(0.75)
    assert parsed.probabilities == pytest.approx({"true": 0.75, "false": 0.25})


def test_JDG_F_01_verdict_round_trips_and_forbids_self_grading() -> None:
    parsed = parse_answer(CHOICE, '{"answer": "C", "probability": 0.55}')
    v = to_verdict(CHOICE, parsed, backend="fake", cost_usd=0.001, latency_ms=12, trace_id="t",
                   judge_id="p2.judge", producer_id="p3.writer")  # fmt: skip
    assert Verdict.model_validate_json(v.model_dump_json()) == v
    assert (v.answer, v.confidence_source, v.question_id) == ("C", "self_report", "loop.best")
    with pytest.raises(ValidationError, match="grade its own work"):
        to_verdict(CHOICE, parsed, backend="fake", cost_usd=0, latency_ms=0, trace_id="t",
                   judge_id="p3.writer", producer_id="p3.writer")  # fmt: skip
