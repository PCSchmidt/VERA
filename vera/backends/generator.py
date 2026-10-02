"""Generator backend: free-text chat completions for the research loop (ideas, experiment code, write-up).

The judge backends answer one bounded question; the loop's producers need prose and code. Every call still goes
through `metered_call` (budget check before, ledger record after, also for failures), so a loop run's spend is one
ledger. The reply is returned as text; parsing and validation belong to the stage that asked.

Reasoning models (GLM-5.3 Flash, Sonnet 5.5 on OpenRouter) cannot have reasoning switched off, but its amount can be
set: `reasoning={"effort": "minimal"}` took a code task from thousands of reasoning tokens (and, at 8000 max, an
empty reply) to 129 reasoning tokens and a full answer in the Increment 2 probe. `max_tokens` still has to leave room
for reasoning as well as the answer, and the pre-call estimate prices the whole of it.
"""

from __future__ import annotations

import httpx

from vera.backends import api_key, post_with_retry
from vera.backends.openrouter import API, Prices, catalogue_prices
from vera.ledger import CallResult, Ledger, metered_call, new_trace_id
from vera.schemas import Budget


class OpenRouterGenerator:
    def __init__(
        self,
        name: str,
        model: str,
        *,
        ledger: Ledger,
        budget: Budget,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        provider_sort: str | None = "price",
        reasoning: dict | None = None,
        prices: Prices | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.name, self.model, self.ledger, self.budget = name, model, ledger, budget
        self.max_tokens, self.temperature, self.provider_sort = max_tokens, temperature, provider_sort
        self.reasoning = reasoning
        self.client = client or httpx.Client(timeout=300)
        self.prices = prices or catalogue_prices(model, self.client)

    def _estimate(self, messages: list[dict[str, str]]) -> float:
        chars = sum(len(m["content"]) for m in messages)
        return (chars / 3 + 50) * self.prices.input_per_token + self.max_tokens * self.prices.output_per_token

    def _call(self, messages: list[dict[str, str]]) -> CallResult:
        body = {
            "model": self.model, "messages": messages, "temperature": self.temperature,
            "max_tokens": self.max_tokens, "usage": {"include": True},
        }  # fmt: skip
        if self.reasoning is not None:
            body["reasoning"] = self.reasoning  # e.g. {"effort": "minimal"}: the models cannot switch reasoning off
        if self.provider_sort:
            body["provider"] = {"sort": self.provider_sort}
        resp = post_with_retry(
            self.client, f"{API}/chat/completions", json=body,
            headers={"Authorization": f"Bearer {api_key('OPENROUTER_API_KEY')}"},
        )
        if resp.is_error:
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
            provider=data.get("provider"),
        )

    def generate(self, system: str, prompt: str, *, component: str) -> str:
        """One metered completion. `component` names the loop stage in the ledger (e.g. "p3.ideate")."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        result = metered_call(
            lambda: self._call(messages),
            ledger=self.ledger, budget=self.budget, component=component, backend=self.name, model=self.model,
            estimate_usd=self._estimate(messages), trace_id=new_trace_id(),
        )  # fmt: skip
        return result.text
