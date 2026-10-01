"""OpenRouter chat-model backend: one metered call per question.

Prompts come from `vera.judge.build_messages` and replies are parsed by
`vera.judge.parse_answer`. When the model supports it, the call asks for
token log-probabilities, and the probabilities at the answer's first token
become `answer_probs` (confidence source "logprobs"); otherwise confidence is
self-reported. Cost is OpenRouter's own figure for the call (`usage.cost`);
the pre-call budget estimate uses the model's catalogue prices.

Reasoning is off by default (`reasoning=False`): the cheap path must answer
fast (JDG-P-02), and a reasoning model spends a small `max_tokens` on hidden
reasoning and returns no answer. `reasoning=None` sends no setting (the
provider's default), for endpoints where reasoning can't be disabled.

OpenRouter serves a model through several providers at different prices
(DeepSeek V4.1 Flash: $0.02 to $0.31 per million input tokens on the same
day). `provider_sort="price"` (default) asks for the cheapest available,
which is the price the catalogue and T1 assume; `None` leaves OpenRouter's
default load balancing. Some models (e.g. Claude) still write a
line of working before the JSON; `max_tokens` leaves room for it and the
parser takes the last JSON object.
"""

from __future__ import annotations

import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from vera.backends import api_key
from vera.judge import build_messages, parse_answer, to_verdict
from vera.ledger import CallResult, Ledger, metered_call, new_trace_id
from vera.schemas import Budget, Question, QuestionType, Verdict

API = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class Prices:
    input_per_token: float
    output_per_token: float
    logprobs: bool = False


def catalogue_prices(model: str, client: httpx.Client | None = None) -> Prices:
    """Current per-token prices and logprob support from OpenRouter's public model list."""
    client = client or httpx.Client(timeout=60)
    for attempt in range(3):  # this machine has intermittent DNS failures
        try:
            data = client.get(f"{API}/models").json()["data"]
            break
        except httpx.TransportError:
            if attempt == 2:
                raise
            time.sleep(5)
    entry = next((m for m in data if m["id"] == model), None)
    if entry is None:
        raise KeyError(f"{model} not in the OpenRouter catalogue")
    p = entry["pricing"]
    return Prices(float(p["prompt"]), float(p["completion"]), "logprobs" in (entry.get("supported_parameters") or []))


def _clean(token: str) -> str:
    return token.strip().strip('"').strip().lower()


def answer_token_probs(question: Question, logprobs: list[dict]) -> dict[str, float] | None:
    """Probabilities per candidate answer, read at the first token of the JSON "answer" value."""
    text = ""
    for i, tok in enumerate(logprobs):
        before = text
        text += tok.get("token", "")
        if re.search(r'"answer"\s*:\s*"?\s*$', before) and _clean(tok.get("token", "")):
            top = tok.get("top_logprobs") or []
            return _candidates(question, [(t.get("token", ""), math.exp(t.get("logprob", -99))) for t in top])
        if i > 400:
            break
    return None


def _candidates(question: Question, top: list[tuple[str, float]]) -> dict[str, float] | None:
    probs: dict[str, float] = {}
    if question.type is QuestionType.BOOLEAN:
        for tok, p in top:
            c = _clean(tok)
            for word in ("true", "false"):
                if c and word.startswith(c):
                    probs[word] = probs.get(word, 0.0) + p
    elif question.type is QuestionType.CHOICE:
        options = question.options or []
        firsts = [o.lower()[:1] for o in options]
        if len(set(firsts)) < len(firsts):
            return None  # options share a first character: one token can't tell them apart
        for tok, p in top:
            c = _clean(tok)
            for o in options:
                if c and o.lower().startswith(c):
                    probs[o] = probs.get(o, 0.0) + p
    else:
        lo, hi = question.scale or (1, 5)
        for tok, p in top:
            c = _clean(tok)
            if c.lstrip("-").isdigit() and lo <= int(c) <= hi:
                probs[str(int(c))] = probs.get(str(int(c)), 0.0) + p
    return probs or None


class OpenRouterBackend:
    def __init__(
        self,
        name: str,
        model: str,
        cost_rank: int,
        *,
        ledger: Ledger,
        budget: Budget,
        judge_id: str = "p2.judge",
        prices: Prices | None = None,
        client: httpx.Client | None = None,
        max_tokens: int = 512,
        reasoning: bool | None = False,
        provider_sort: str | None = "price",
        component: str = "p2.backend",
    ) -> None:
        self.name, self.model, self.cost_rank = name, model, cost_rank
        self.ledger, self.budget, self.judge_id, self.component = ledger, budget, judge_id, component
        self.client = client or httpx.Client(timeout=90)
        self.prices = prices or catalogue_prices(model, self.client)
        self.max_tokens, self.reasoning, self.provider_sort = max_tokens, reasoning, provider_sort

    def _estimate(self, messages: list[dict[str, str]]) -> float:
        chars = sum(len(m["content"]) for m in messages)
        return (chars / 3 + 50) * self.prices.input_per_token + self.max_tokens * self.prices.output_per_token

    def _call(self, messages: list[dict[str, str]]) -> CallResult:
        body = {
            "model": self.model, "messages": messages, "temperature": 0, "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}, "usage": {"include": True},
        }  # fmt: skip
        if self.reasoning is not None:
            body["reasoning"] = {"enabled": self.reasoning}
        if self.provider_sort:
            body["provider"] = {"sort": self.provider_sort}
        if self.prices.logprobs:
            body |= {"logprobs": True, "top_logprobs": 5}
        resp = self.client.post(
            f"{API}/chat/completions", json=body, headers={"Authorization": f"Bearer {api_key('OPENROUTER_API_KEY')}"}
        )
        if resp.is_error:  # keep the provider's reason: metered_call writes it to the ledger
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        choice, usage = data["choices"][0], data.get("usage") or {}
        return CallResult(
            text=choice["message"].get("content") or "",
            model=data.get("model", self.model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            cost_usd=float(usage.get("cost") or 0.0),
            extra={"logprobs": (choice.get("logprobs") or {}).get("content") or []},
        )

    def ask(self, state: str, questions: Sequence[Question]) -> list[Verdict]:
        verdicts = []
        for q in questions:
            messages, trace_id = build_messages(state, q), new_trace_id()
            result = metered_call(
                lambda m=messages: self._call(m), ledger=self.ledger, budget=self.budget, component=self.component,
                backend=self.name, model=self.model, estimate_usd=self._estimate(messages), trace_id=trace_id,
            )  # fmt: skip
            probs = answer_token_probs(q, result.extra["logprobs"]) if result.extra.get("logprobs") else None
            parsed = parse_answer(q, result.text, probs)
            latency = result.extra["latency_ms"]
            verdicts.append(to_verdict(q, parsed, backend=self.name, cost_usd=result.cost_usd, latency_ms=latency,
                                       trace_id=trace_id, judge_id=self.judge_id))  # fmt: skip
        return verdicts
