"""The T1 cheap judge path, as one function (docs/04 T1, decided 2026-10-01).

Jev answers first; GLM-5.3 Flash takes anything below the default threshold 0.7 (and answers alone when no Jev
key is set). The loop's own questions (ids starting with `vera.loop.LOOP_PREFIX`, "loop.") skip Jev and go straight
to GLM. Nothing else in VERA builds its own router.
"""

from __future__ import annotations

from collections.abc import Sequence

from vera.backends import api_key
from vera.bench.candidates import make_backend
from vera.judge.router import Router
from vera.ledger import Ledger
from vera.loop import LIT_PREFIX, LOOP_PREFIX
from vera.schemas import Budget, JudgeBackend, Question, RoutingPolicy, Verdict

# GLM-5.3 Flash cannot switch its reasoning off, and the loop's questions carry long material (idea texts, whole
# reports): at the benchmark's 2048 tokens, two of three idea scores in the first live run came back empty because
# the reasoning used the whole allowance. Room for the reasoning and the answer; the estimate stays an upper bound.
LOOP_JUDGE_MAX_TOKENS = 6000
# Even so, at the provider's default reasoning 4 of 11 loop judge calls in the first full run used 5000-6000 output
# tokens (up to 190 s) on trivial questions, one returning nothing. "minimal" took the generator's code task from
# thousands of reasoning tokens to about 130. This differs from the T1 benchmark's configuration (provider default);
# the Increment 2 re-test on the loop's real gate decisions measures the path as configured here.
LOOP_JUDGE_REASONING = {"effort": "minimal"}


class CheapPath:
    """Same `ask` as `Router`: loop questions to the GLM-only router, the rest to Jev -> GLM, order kept."""

    def __init__(self, default: Router, loop: Router, loop_prefix: str | tuple[str, ...] = (LOOP_PREFIX, LIT_PREFIX)):
        self.default, self.loop, self.loop_prefix = default, loop, loop_prefix  # str.startswith takes a tuple

    def ask(self, state: str, questions: Sequence[Question], threshold: float | None = None) -> list[Verdict]:
        by_id: dict[str, Verdict] = {}
        for router, group in (
            (self.loop, [q for q in questions if q.id.startswith(self.loop_prefix)]),
            (self.default, [q for q in questions if not q.id.startswith(self.loop_prefix)]),
        ):
            if group:
                by_id.update({v.question_id: v for v in router.ask(state, group, threshold)})
        return [by_id[q.id] for q in questions]


def cheap_path(
    *,
    ledger: Ledger,
    budget: Budget,
    component: str = "p2.cheap_path",
    backends: Sequence[JudgeBackend] | None = None,
) -> CheapPath:
    """The T1 path, writing to `ledger` and charging `budget`. `backends` = (jev, glm) overrides, for tests."""
    if backends is None:
        glm = make_backend("glm-flash", ledger=ledger, budget=budget, component=component)
        glm.max_tokens = max(glm.max_tokens, LOOP_JUDGE_MAX_TOKENS)
        glm.reasoning = LOOP_JUDGE_REASONING
        if not jev_available():  # no Jev key: GLM answers every question (the app's bring-your-own-key case)
            glm.cost_rank = 1
            return CheapPath(Router([glm], RoutingPolicy()), Router([glm], RoutingPolicy()))
        jev = make_backend("jev", ledger=ledger, budget=budget, component=component)
        jev.cost_rank, glm.cost_rank = 1, 2  # both are rank 1 in the benchmark; here Jev goes first
        backends = (jev, glm)
    jev, glm = backends
    policy = RoutingPolicy()  # default threshold 0.7, one escalation
    return CheapPath(Router([jev, glm], policy), Router([glm], policy))


def jev_available() -> bool:
    """Is the user's own Jev (TypeSafe) key set? Bring-your-own-key users usually have only an OpenRouter key."""
    try:
        api_key("TYPESAFE_AI_API_KEY")
    except KeyError:
        return False
    return True
