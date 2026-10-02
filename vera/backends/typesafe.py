"""TypeSafe Jev backend (decision model): all questions in one metered call.

API: POST https://api.typesafe.ai/v1/systemone with a state and typed
questions (https://docs.typesafe.ai). Mapping from VERA's question types:

- BOOLEAN -> "noul": returns p(yes); answer = p >= 0.5, confidence = max(p, 1 - p);
- CHOICE  -> "choice" with the options as criteria: answer = chosen option,
  confidence = its probability;
- SCORE   -> "score" with one level per integer on the scale: answer =
  scale start + level index, confidence = that level's probability.

Confidence is the probability of the chosen answer, the same definition as
the other backends (not Jev's own `confidence` statistic, which is kept in
`probabilities`' shape), and its source is "logprobs" (the model's own
distribution; docs/03 v0.6). One ledger record per call; its cost is split
evenly across the call's verdicts.

Price: TypeSafe publishes input-only pricing (output free). The per-token
price is passed in (see docs/04 T1 for its source) and used for both the
budget estimate and the recorded cost; check it against the TypeSafe console.

Terms (typesafe.ai/legal/mca, §2.3(b)): never use Jev's output to distil or
train a model. Benchmark results are published (Chris's decision, docs/04 T1,
risk R4).
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from vera.backends import api_key, post_with_retry
from vera.judge import ParsedAnswer, to_verdict
from vera.ledger import CallResult, Ledger, metered_call, new_trace_id
from vera.schemas import Budget, Question, QuestionType, Verdict

API = "https://api.typesafe.ai/v1/systemone"


def question_payload(q: Question) -> dict:
    if q.type is QuestionType.BOOLEAN:
        return {"type": "noul", "instructions": q.text}
    if q.type is QuestionType.CHOICE:
        return {"type": "choice", "instructions": q.text, "criteria": {o: o for o in q.options or []}}
    lo, hi = q.scale or (1, 5)
    rubric = f" ({q.rubric})" if q.rubric else ""
    levels = [f"{v}{rubric if v == hi else ''}" for v in range(lo, hi + 1)]
    return {"type": "score", "instructions": q.text, "criteria": levels}


def parse_jev(q: Question, ans: dict | None) -> ParsedAnswer:
    """One Jev answer as a ParsedAnswer; anything unexpected is malformed (confidence 0)."""
    try:
        if q.type is QuestionType.BOOLEAN:
            p = float(ans["noul"])
            if not 0.0 <= p <= 1.0:
                raise ValueError
            return ParsedAnswer(p >= 0.5, max(p, 1 - p), "logprobs", {"true": p, "false": 1 - p})
        probs = {str(k): float(v) for k, v in ans["probabilities"].items()}
        if q.type is QuestionType.CHOICE:
            choice = ans["choice"]
            if choice not in (q.options or []):
                raise ValueError
            return ParsedAnswer(choice, probs.get(choice, 0.0), "logprobs", probs)
        lo, _hi = q.scale or (1, 5)
        level = int(round(float(ans["score"])))
        by_value = {str(lo + int(k)): v for k, v in probs.items()}
        return ParsedAnswer(lo + level, probs.get(str(level), 0.0), "logprobs", by_value)
    except (KeyError, TypeError, ValueError):
        return ParsedAnswer("", 0.0, "none")


class JevBackend:
    def __init__(
        self,
        name: str,
        cost_rank: int,
        *,
        ledger: Ledger,
        budget: Budget,
        input_price_per_token: float,
        model: str = "jev-latest",
        judge_id: str = "p2.judge",
        client: httpx.Client | None = None,
        component: str = "p2.backend",
    ) -> None:
        self.name, self.cost_rank, self.model = name, cost_rank, model
        self.ledger, self.budget, self.judge_id, self.component = ledger, budget, judge_id, component
        self.price = input_price_per_token
        self.client = client or httpx.Client(timeout=60)

    def _call(self, body: dict) -> CallResult:
        resp = post_with_retry(
            self.client, API, json=body, headers={"Authorization": f"Bearer {api_key('TYPESAFE_AI_API_KEY')}"}
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage") or {}
        tokens_in = usage.get("input_tokens")
        return CallResult(
            text="", model=data.get("model", self.model), input_tokens=tokens_in,
            output_tokens=usage.get("output_tokens"), cost_usd=(tokens_in or 0) * self.price,
            extra={"answers": data.get("answers") or {}},
        )  # fmt: skip

    def ask(self, state: str, questions: Sequence[Question]) -> list[Verdict]:
        ids = {f"q{i}": q for i, q in enumerate(questions)}  # Jev keys must be simple ids
        body = {"state": state, "model": self.model, "questions": {k: question_payload(q) for k, q in ids.items()}}
        estimate = (len(state) / 3 + 200 * len(questions)) * self.price
        trace_id = new_trace_id()
        result = metered_call(
            lambda: self._call(body), ledger=self.ledger, budget=self.budget, component=self.component,
            backend=self.name, model=self.model, estimate_usd=estimate, trace_id=trace_id,
        )  # fmt: skip
        share = result.cost_usd / max(1, len(questions))
        return [
            to_verdict(
                q,
                parse_jev(q, result.extra["answers"].get(k)),
                backend=self.name,
                cost_usd=share,
                latency_ms=result.extra["latency_ms"],
                trace_id=trace_id,
                judge_id=self.judge_id,
            )  # fmt: skip
            for k, q in ids.items()
        ]
