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


# JDG-F-07 (Increment 8): a question with an entry here is answered only by these backends, in order (escalating below
# the threshold), wherever it is asked. Chosen from the measurement against the reference judge
# (data/results/judge8_test.json): no backend met JDG-P-01 and JDG-P-03 on these questions; Jev then GLM agreed best
# (89%, 95%, 89%); Chris chose to keep it, with the audit confirming a "no" on the two harder questions (CONFIRM_NO).
QUESTION_ROUTES: dict[str, tuple[str, ...]] = {
    "claim.within_quote": ("jev", "glm-flash"),
    "sentence.no_fact": ("jev", "glm-flash"),
    "paper.inference_follows": ("jev", "glm-flash"),
}
# In the audit, a confident "no" on these questions is re-asked to the reference judge before it can fail (AUD-F-13).
CONFIRM_NO: dict[str, str] = {"claim.within_quote": "sonnet-ref", "paper.inference_follows": "sonnet-ref"}


class CheapPath:
    """Same `ask` as `Router`: a question in `routes` to its own router (JDG-F-07); loop and literature-stage questions
    to the GLM-only router; the rest to Jev -> GLM. Order kept."""

    def __init__(self, default: Router, loop: Router, loop_prefix: str | tuple[str, ...] = (LOOP_PREFIX, LIT_PREFIX),
                 routes: dict[str, Router] | None = None) -> None:  # fmt: skip
        self.default, self.loop, self.loop_prefix = default, loop, loop_prefix  # str.startswith takes a tuple
        self.routes = routes or {}

    def router_for(self, question: Question) -> Router:
        if question.id in self.routes:
            return self.routes[question.id]
        return self.loop if question.id.startswith(self.loop_prefix) else self.default

    def ask(self, state: str, questions: Sequence[Question], threshold: float | None = None) -> list[Verdict]:
        by_id: dict[str, Verdict] = {}
        groups: dict[int, tuple[Router, list[Question]]] = {}
        for q in questions:
            router = self.router_for(q)
            groups.setdefault(id(router), (router, []))[1].append(q)
        for router, group in groups.values():
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
            only = Router([glm], RoutingPolicy())
            return CheapPath(only, only, routes=dict.fromkeys(QUESTION_ROUTES, only))
        jev = make_backend("jev", ledger=ledger, budget=budget, component=component)
        jev.cost_rank, glm.cost_rank = 1, 2  # both are rank 1 in the benchmark; here Jev goes first
        backends = (jev, glm)
    jev, glm = backends
    policy = RoutingPolicy()  # default threshold 0.7, one escalation
    by_name = {"jev": jev, "glm-flash": glm}
    routers: dict[tuple[str, ...], Router] = {}
    routes = {}
    for qid, names in QUESTION_ROUTES.items():
        chain = tuple(n for n in names if n in by_name)  # a backend not configured is skipped
        routes[qid] = routers.setdefault(chain, Router([by_name[n] for n in chain], policy))
    return CheapPath(Router([jev, glm], policy), Router([glm], policy), routes=routes)


def confirmer(*, ledger: Ledger, budget: Budget, component: str = "p2.confirm") -> JudgeBackend:
    """The reference judge that confirms an audit's "no" on the questions in `CONFIRM_NO` (AUD-F-13)."""
    return make_backend("sonnet-ref", ledger=ledger, budget=budget, component=component)


def jev_available() -> bool:
    """Is the user's own Jev (TypeSafe) key set? Bring-your-own-key users usually have only an OpenRouter key."""
    try:
        api_key("TYPESAFE_AI_API_KEY")
    except KeyError:
        return False
    return True
