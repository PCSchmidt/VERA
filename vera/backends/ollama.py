"""Local model backend through Ollama (T1 option (b); risk R4's local fallback): one metered call per question.

Talks to the Ollama server on this machine (`/api/chat`, default
http://localhost:11434), so it works offline and costs nothing per token.
Prompts and parsing are shared with the other chat backends
(`vera.judge.build_messages` / `parse_answer`). The call asks for JSON
output (`json_format`), thinking off, temperature 0, and, if `logprobs`,
token log-probabilities; when the server returns them for the answer token,
those probabilities become the confidence (source "logprobs"), else it is
self-reported. Ollama 0.34.2 returns them for the first token only, so the
benchmark runs with `logprobs=False`.

Cost: the ledger records $0 (no per-token price). The compute is not free,
so the call's latency is the cost to watch; `seconds_per_call` in the
benchmark report covers it.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from vera.backends.openrouter import answer_token_probs
from vera.judge import build_messages, parse_answer, to_verdict
from vera.ledger import CallResult, Ledger, metered_call, new_trace_id
from vera.schemas import Budget, Question, Verdict

HOST = "http://localhost:11434"


class OllamaBackend:
    def __init__(
        self,
        name: str,
        model: str,
        cost_rank: int,
        *,
        ledger: Ledger,
        budget: Budget,
        judge_id: str = "p2.judge",
        host: str = HOST,
        client: httpx.Client | None = None,
        max_tokens: int = 512,
        logprobs: bool = True,
        json_format: bool = True,
        component: str = "p2.backend",
    ) -> None:
        self.name, self.model, self.cost_rank = name, model, cost_rank
        self.ledger, self.budget, self.judge_id, self.component = ledger, budget, judge_id, component
        self.host, self.max_tokens, self.logprobs = host.rstrip("/"), max_tokens, logprobs
        self.json_format = json_format
        self.client = client or httpx.Client(timeout=300)  # the first call loads the model into memory

    def _call(self, messages: list[dict[str, str]]) -> CallResult:
        body = {
            "model": self.model, "messages": messages, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": self.max_tokens},
        }  # fmt: skip
        if self.json_format:
            body["format"] = "json"
        if self.logprobs:
            body |= {"logprobs": True, "top_logprobs": 5}
        resp = self.client.post(f"{self.host}/api/chat", json=body)
        if resp.is_error:  # keep the server's reason: metered_call writes it to the ledger
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return CallResult(
            text=(data.get("message") or {}).get("content") or "",
            model=data.get("model", self.model),
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            cost_usd=0.0,
            extra={"logprobs": data.get("logprobs") or []},
        )

    def ask(self, state: str, questions: Sequence[Question]) -> list[Verdict]:
        verdicts = []
        for q in questions:
            messages, trace_id = build_messages(state, q), new_trace_id()
            result = metered_call(
                lambda m=messages: self._call(m), ledger=self.ledger, budget=self.budget, component=self.component,
                backend=self.name, model=self.model, estimate_usd=0.0, trace_id=trace_id,
            )  # fmt: skip
            probs = answer_token_probs(q, result.extra["logprobs"]) if result.extra.get("logprobs") else None
            parsed = parse_answer(q, result.text, probs)
            verdicts.append(to_verdict(q, parsed, backend=self.name, cost_usd=0.0,
                                       latency_ms=result.extra["latency_ms"], trace_id=trace_id,
                                       judge_id=self.judge_id))  # fmt: skip
        return verdicts
