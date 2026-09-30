"""The T1 candidate backends and the reference judge (docs/04 T1), shared by the smoke run and the benchmark.

OpenRouter prices come from its catalogue at construction time; Jev's price
is fixed (docs/04 T1: $0.042 per million input tokens, output free).
Jev results are not published without TypeSafe's written consent (risk R4).
"""

from __future__ import annotations

from vera.backends.openrouter import OpenRouterBackend
from vera.backends.typesafe import JevBackend
from vera.ledger import Ledger
from vera.schemas import Budget

JEV_INPUT_PRICE_PER_TOKEN = 4.2e-8

# name -> (OpenRouter model id, cost rank, reasoning, max_tokens); the reference judge ranks last.
# Cheap models answer without reasoning (latency, JDG-P-02). Sonnet 5.5's endpoint won't disable
# reasoning (HTTP 400), nor does GLM-5.3 Flash's; they run at the provider default with room for it.
OPENROUTER = {
    "mimo-flash": ("xiaomi/mimo-v2.6-flash", 1, False, 512),
    "deepseek-flash": ("deepseek/deepseek-v4.1-flash", 1, False, 512),
    "glm-flash": ("z-ai/glm-5.3-flash", 1, None, 2048),  # reasoning mandatory here too
    "sonnet-ref": ("anthropic/claude-sonnet-5.5", 9, None, 2048),
}
REFERENCE = "sonnet-ref"
NAMES = [*OPENROUTER, "jev"]


def make_backend(name: str, *, ledger: Ledger, budget: Budget, component: str = "p2.bench"):
    if name == "jev":
        return JevBackend("jev", 1, ledger=ledger, budget=budget, input_price_per_token=JEV_INPUT_PRICE_PER_TOKEN,
                          component=component)  # fmt: skip
    model, rank, reasoning, max_tokens = OPENROUTER[name]
    return OpenRouterBackend(name, model, rank, ledger=ledger, budget=budget, component=component,
                             reasoning=reasoning, max_tokens=max_tokens)  # fmt: skip
