"""Router (JDG-F-02, JDG-F-03): cheapest backend first, escalate low-confidence verdicts.

For a batch of questions, the router asks the cheapest backend (lowest
`cost_rank`) all of them, then sends only the questions whose confidence is
below their threshold to the next backend, and so on, for at most
`policy.max_escalations` further backends. A question's threshold follows
`RoutingPolicy.threshold_for`: per-call override > per question id > per
question type > default.

The final verdict for a question is the one from the last backend asked; it
has `escalated=True` when a cheaper backend was bypassed. A backend that
raises counts as zero confidence for its questions (the ledger has already
recorded the failed call). If the last backend raises, questions that already
have a verdict from a cheaper backend keep it (its low confidence shows the
escalation failed); the error propagates only if some question has no
verdict at all.
"""

from __future__ import annotations

from collections.abc import Sequence

from vera.schemas import JudgeBackend, Question, RoutingPolicy, Verdict


class Router:
    def __init__(self, backends: Sequence[JudgeBackend], policy: RoutingPolicy | None = None) -> None:
        if not backends:
            raise ValueError("Router needs at least one backend")
        self.backends = sorted(backends, key=lambda b: b.cost_rank)
        self.policy = policy or RoutingPolicy()

    def ask(self, state: str, questions: Sequence[Question], threshold: float | None = None) -> list[Verdict]:
        """One verdict per question, in order. `threshold` overrides the policy for this call."""
        chain = self.backends[: 1 + self.policy.max_escalations]
        final: dict[str, Verdict] = {}
        pending = list(questions)
        for i, backend in enumerate(chain):
            last = i == len(chain) - 1
            try:
                verdicts = backend.ask(state, pending)
            except Exception:
                if last and any(q.id not in final for q in pending):
                    raise
                continue  # everything pending escalates (or keeps its earlier verdict)
            by_id = {v.question_id: v for v in verdicts}
            still = []
            for q in pending:
                v = by_id.get(q.id)
                if v is not None:
                    final[q.id] = v.model_copy(update={"escalated": i > 0})
                if v is None or (not last and v.confidence < self.policy.threshold_for(q, threshold)):
                    still.append(q)
            pending = still
            if not pending:
                break
        missing = [q.id for q in questions if q.id not in final]
        if missing:
            raise RuntimeError(f"no backend returned a verdict for: {', '.join(missing)}")
        return [final[q.id] for q in questions]
