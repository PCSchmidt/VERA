"""Backends against canned API responses (httpx.MockTransport). No network, no keys."""

from __future__ import annotations

import json
import math
from pathlib import Path

import httpx
import pytest

from vera.backends import api_key
from vera.backends.openrouter import OpenRouterBackend, Prices, answer_token_probs
from vera.backends.typesafe import JevBackend, parse_jev, question_payload
from vera.ledger import Ledger
from vera.schemas import Budget, Question, QuestionType

BOOL = Question(id="loop.beats", type=QuestionType.BOOLEAN, text="Does run B beat the baseline?")
CHOICE = Question(id="loop.best", type=QuestionType.CHOICE, text="Best run?", options=["A", "B", "C"])
SCORE = Question(id="aud.clarity", type=QuestionType.SCORE, text="How clear?", scale=(1, 3))


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or")
    monkeypatch.setenv("TYPESAFE_AI_API_KEY", "test-ts")


def lp(token: str, top: dict[str, float]) -> dict:
    return {
        "token": token,
        "logprob": math.log(max(top.values())),
        "top_logprobs": [{"token": t, "logprob": math.log(p)} for t, p in top.items()],
    }


def openrouter_reply(content: str, logprobs: list | None = None, cost: float = 0.0001) -> dict:
    choice = {"message": {"content": content}}
    if logprobs is not None:
        choice["logprobs"] = {"content": logprobs}
    return {
        "model": "deepseek/deepseek-v4.1-flash",
        "choices": [choice],
        "usage": {"prompt_tokens": 210, "completion_tokens": 12, "cost": cost},
    }


def backend(tmp_path: Path, handler, prices: Prices) -> tuple[OpenRouterBackend, Ledger, list]:
    seen: list = []

    def wrap(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer test-or"
        return httpx.Response(200, json=handler(seen[-1]))

    ledger = Ledger(tmp_path / "smoke.jsonl")
    b = OpenRouterBackend(
        "cheap",
        "deepseek/deepseek-v4.1-flash",
        0,
        ledger=ledger,
        budget=Budget(max_usd=1.0, max_wall_seconds=600),
        prices=prices,
        client=httpx.Client(transport=httpx.MockTransport(wrap)),
    )
    return b, ledger, seen


def test_openrouter_logprob_confidence_and_ledger(tmp_path: Path) -> None:
    tokens = [
        lp('{"', {'{"': 1.0}),
        lp("answer", {"answer": 1.0}),
        lp('":', {'":': 1.0}),
        lp(" true", {" true": 0.8, " false": 0.2}),
        lp(', "probability": 0.99}', {"x": 1.0}),
    ]
    b, ledger, seen = backend(
        tmp_path,
        lambda body: openrouter_reply('{"answer": true, "probability": 0.99}', tokens),
        Prices(1e-7, 4e-7, logprobs=True),
    )
    (v,) = b.ask("state", [BOOL])
    assert seen[0]["logprobs"] is True and seen[0]["temperature"] == 0 and seen[0]["usage"] == {"include": True}
    assert (v.answer, v.confidence_source, v.backend) == (True, "logprobs", "cheap")
    assert v.confidence == pytest.approx(0.8) and v.cost_usd == 0.0001
    (r,) = ledger.records()
    assert (r.input_tokens, r.output_tokens, r.cost_usd, r.backend, r.trace_id) == (
        210,
        12,
        0.0001,
        "cheap",
        v.trace_id,
    )


def test_openrouter_without_logprobs_uses_self_report(tmp_path: Path) -> None:
    b, _, seen = backend(
        tmp_path,
        lambda body: openrouter_reply('{"answer": "B", "probability": 0.6}'),
        Prices(1e-7, 3e-7, logprobs=False),
    )
    (v,) = b.ask("state", [CHOICE])
    assert "logprobs" not in seen[0]
    assert (v.answer, v.confidence, v.confidence_source) == ("B", 0.6, "self_report")


def test_openrouter_error_payload_is_recorded(tmp_path: Path) -> None:
    b, ledger, _ = backend(tmp_path, lambda body: {"error": {"message": "rate limited"}}, Prices(1e-7, 3e-7))
    with pytest.raises(RuntimeError):
        b.ask("state", [BOOL])
    assert "rate limited" in ledger.records()[0].error


def test_answer_token_probs_for_choice_and_score() -> None:
    tokens = [lp('{"answer": "', {'{"answer": "': 1.0}), lp("B", {"B": 0.7, "A": 0.2, "C": 0.1})]
    assert answer_token_probs(CHOICE, tokens) == pytest.approx({"B": 0.7, "A": 0.2, "C": 0.1})
    tokens = [lp('{"answer": ', {'{"answer": ': 1.0}), lp("2", {"2": 0.9, "3": 0.05, "7": 0.05})]
    assert answer_token_probs(SCORE, tokens) == pytest.approx({"2": 0.9, "3": 0.05})
    shared = Question(id="x", type=QuestionType.CHOICE, text="?", options=["alpha", "also"])
    assert answer_token_probs(shared, [lp('{"answer": "', {"a": 1.0}), lp("al", {"al": 1.0})]) is None


def test_jev_payload_and_parsing() -> None:
    assert question_payload(BOOL) == {"type": "noul", "instructions": BOOL.text}
    assert question_payload(CHOICE)["criteria"] == {"A": "A", "B": "B", "C": "C"}
    assert question_payload(SCORE)["criteria"] == ["1", "2", "3"]
    p = parse_jev(BOOL, {"type": "noul", "noul": 0.2})
    assert (p.answer, p.confidence, p.source) == (False, 0.8, "logprobs")
    p = parse_jev(SCORE, {"type": "score", "score": 1.0, "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2}})
    assert (p.answer, p.confidence) == (2, 0.7) and p.probabilities == {"1": 0.1, "2": 0.7, "3": 0.2}
    assert parse_jev(CHOICE, {"choice": "Z", "probabilities": {}}).source == "none"
    assert parse_jev(BOOL, None).confidence == 0.0


def test_jev_backend_one_call_cost_split(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-ts"
        assert set(body["questions"]) == {"q0", "q1"} and body["model"] == "jev-latest"
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 1000, "output_tokens": 40},
                "answers": {
                    "q0": {"type": "noul", "noul": 0.9},
                    "q1": {"type": "choice", "choice": "C", "probabilities": {"A": 0.1, "B": 0.1, "C": 0.8}},
                },
            },
        )

    ledger = Ledger(tmp_path / "jev.jsonl")
    jev = JevBackend(
        "jev",
        0,
        ledger=ledger,
        budget=Budget(max_usd=1.0, max_wall_seconds=60),
        input_price_per_token=4.2e-7,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    v1, v2 = jev.ask("state", [BOOL, CHOICE])
    assert (v1.answer, v2.answer, v2.confidence) == (True, "C", 0.8)
    assert v1.cost_usd == pytest.approx(2.1e-4) and v1.trace_id == v2.trace_id
    (r,) = ledger.records()
    assert (r.model, r.input_tokens, r.cost_usd) == ("jev-1.13.0", 1000, pytest.approx(4.2e-4))


def test_api_key_reads_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY")
    env = tmp_path / ".env"
    env.write_text("# comment\nOPENROUTER_API_KEY=abc123\n", encoding="utf-8")
    assert api_key("OPENROUTER_API_KEY", env) == "abc123"
    with pytest.raises(KeyError):
        api_key("MISSING_KEY", env)
