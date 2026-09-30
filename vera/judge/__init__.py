"""Judge layer (P2): prompts, answer parsing and verdicts for Choice, Score and Boolean questions (JDG-F-01).

A backend sends `build_messages(state, question)` to its model and hands the
reply to `parse_answer`. The model is asked for one JSON object,
`{"answer": ..., "probability": p}`, where p is its probability that the
answer is correct. Confidence comes from token log-probabilities when the
backend supplies them (`answer_probs`: probability per candidate answer),
else from the self-reported p. Anything malformed or out of range becomes a
zero-confidence result with source "none", so the router escalates it; it
never raises and never returns a bare value (CLAUDE.md: every judgment is a
Verdict).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from vera.schemas import Question, QuestionType, Verdict

MALFORMED = ""  # the answer recorded for a malformed reply (confidence 0, source "none")

SYSTEM_PROMPT = (
    "You are a strict, careful judge. Answer the single question about the material given, using only that "
    "material. Reply with one JSON object and nothing else: "
    '{"answer": <answer>, "probability": <number from 0 to 1 that your answer is correct>}.'
)


def answer_format(question: Question) -> str:
    if question.type is QuestionType.BOOLEAN:
        return "The answer is true or false (JSON booleans)."
    if question.type is QuestionType.CHOICE:
        return "The answer is exactly one of these options, as a JSON string: " + json.dumps(question.options)
    lo, hi = question.scale or (1, 5)
    rubric = f" Rubric: {question.rubric}" if question.rubric else ""
    return f"The answer is an integer from {lo} to {hi}.{rubric}"


def build_messages(state: str, question: Question) -> list[dict[str, str]]:
    user = f"Material:\n{state}\n\nQuestion: {question.text}\n{answer_format(question)}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


@dataclass
class ParsedAnswer:
    answer: bool | int | str
    confidence: float
    source: str  # "logprobs" | "self_report" | "none"
    probabilities: dict[str, float] | None = None


def _json_object(text: str) -> dict | None:
    """The last JSON object in the reply that has an "answer" key (a model may write working first)."""
    decoder, found = json.JSONDecoder(), None
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, match.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "answer" in obj:
            found = obj
    return found


def _coerce(question: Question, raw: object) -> bool | int | str | None:
    """The answer in the question's type, or None if it isn't a valid answer."""
    if question.type is QuestionType.BOOLEAN:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in {"true", "false"}:
            return raw.strip().lower() == "true"
        return None
    if question.type is QuestionType.CHOICE:
        options = question.options or []
        if isinstance(raw, str):
            exact = [o for o in options if o == raw.strip()]
            folded = [o for o in options if o.lower() == raw.strip().lower()]
            return (exact or folded or [None])[0]
        return None
    lo, hi = question.scale or (1, 5)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)) and float(raw).is_integer() and lo <= int(raw) <= hi:
        return int(raw)
    if isinstance(raw, str) and raw.strip().lstrip("-").isdigit() and lo <= int(raw) <= hi:
        return int(raw)
    return None


def _key(answer: bool | int | str) -> str:
    return str(answer).lower() if isinstance(answer, bool) else str(answer)


def parse_answer(question: Question, text: str, answer_probs: dict[str, float] | None = None) -> ParsedAnswer:
    """Parse a model reply. `answer_probs` maps candidate answers (as strings) to token probabilities."""
    obj = _json_object(text)
    answer = _coerce(question, obj.get("answer")) if obj else None
    if answer is None:
        return ParsedAnswer(MALFORMED, 0.0, "none")
    if answer_probs:
        probs = {k: float(v) for k, v in answer_probs.items()}
        total = sum(probs.values())
        if total > 0:
            probs = {k: v / total for k, v in probs.items()}
            return ParsedAnswer(answer, min(1.0, max(0.0, probs.get(_key(answer), 0.0))), "logprobs", probs)
    p = obj.get("probability")
    if isinstance(p, (int, float)) and not isinstance(p, bool) and 0.0 <= float(p) <= 1.0:
        return ParsedAnswer(answer, float(p), "self_report")
    return ParsedAnswer(answer, 0.0, "none")  # valid answer but no usable confidence: escalate


def to_verdict(
    question: Question,
    parsed: ParsedAnswer,
    *,
    backend: str,
    cost_usd: float,
    latency_ms: int,
    trace_id: str,
    judge_id: str,
    producer_id: str | None = None,
    escalated: bool = False,
) -> Verdict:
    return Verdict(
        question_id=question.id,
        answer=parsed.answer,
        probabilities=parsed.probabilities,
        confidence=parsed.confidence,
        confidence_source=parsed.source,
        backend=backend,
        escalated=escalated,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        trace_id=trace_id,
        producer_id=producer_id,
        judge_id=judge_id,
    )
