"""Topic scoping and confirmation (RSH-F-08).

The first stage turns a topic and the run's output guidance into a `ScopedQuestion`: a proposed question, why it is
researchable, whether it is empirical, and a candidate parent problem or the reason there is none. The generator writes
it, the judge path gates it (`lit.question_scoped`, a verdict from a component other than the producer), and the run
then **stops and waits** for the user: `scope.json` holds the proposal with status `proposed`, and nothing after
scoping runs until `confirm_scope` records who confirmed (or edited) the question and when. Scoping has its own
spending cap; nothing more is spent before the confirmation.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

from vera.literature import questions
from vera.literature.deps import LitDeps
from vera.loop.stages import _extract_json, _stop, _write_json, ask_gate, stage_result
from vera.schemas import ScopedQuestion

SCOPE_FILE = "scope.json"
MAX_ATTEMPTS = 2

SCOPE_SYSTEM = (
    "You are a research scientist scoping a research topic into one specific, researchable question. Reply only "
    "with what is asked, in the requested format."
)


class ScopeNotConfirmedError(RuntimeError):
    """A stage after scoping was asked to run before the scoped question was confirmed."""


def scope_prompt(deps: LitDeps) -> str:
    topic, g = deps.spec.topic, deps.spec.guidance
    return (
        f"Topic: {topic.text}\n\n"
        "Propose ONE specific research question on this topic that a short literature review could address and, if "
        "it is empirical, that small CPU-scale experiments (minutes each, a laptop, public datasets and public code) "
        "could answer. Say why it is researchable and whether it is empirical. If it is empirical, name a candidate "
        "parent problem (an arXiv id or DOI of a method paper with public code) or say why you cannot name one; if "
        "it is not empirical, leave the parent out.\n\n"
        f"The final paper's guidance: format {g.format}" + (f"; emphasis: {g.emphasis}" if g.emphasis else "")
        + "".join(f"; {c}" for c in g.constraints)
        + '.\n\nReply with a JSON object: {"question": "...", "why_researchable": "...", "empirical": true or false, '
        '"candidate_parent": "..." or null, "no_parent_reason": "..." or null}.'
    )  # fmt: skip


def parse_scope(reply: str, topic_id: str) -> ScopedQuestion | None:
    """The proposal in a model reply, or None when it has no usable question."""
    data = _extract_json(reply, "{", "}")
    if not isinstance(data, dict):
        return None
    try:
        return ScopedQuestion(
            topic_id=topic_id,
            question=str(data.get("question") or ""),
            why_researchable=str(data.get("why_researchable") or ""),
            empirical=bool(data.get("empirical")),
            candidate_parent=(str(data["candidate_parent"]) if data.get("candidate_parent") else None)
            if data.get("empirical") else None,
            no_parent_reason=str(data["no_parent_reason"]) if data.get("no_parent_reason") else None,
        )  # fmt: skip
    except ValueError:
        return None


def read_scope(run_dir: Path) -> ScopedQuestion | None:
    path = run_dir / SCOPE_FILE
    if not path.exists():
        return None
    return ScopedQuestion.model_validate(json.loads(path.read_text(encoding="utf-8")))


def write_scope(run_dir: Path, scoped: ScopedQuestion) -> None:
    (run_dir / SCOPE_FILE).write_text(json.dumps(scoped.model_dump(mode="json"), indent=1), encoding="utf-8")


def confirm_scope(
    run_dir: Path, who: str, *, question: str | None = None, now: dt.datetime | None = None
) -> ScopedQuestion:
    """Record the user's confirmation of the proposed question, or their edit of it (`question`). Needs a name."""
    if not who or not who.strip():
        raise ValueError("a confirmation must say who confirmed")
    scoped = read_scope(run_dir)
    if scoped is None:
        raise FileNotFoundError(f"no {SCOPE_FILE} in {run_dir}: the run has not proposed a question yet")
    stamp = (now or dt.datetime.now(dt.UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    update: dict = {"status": "confirmed", "confirmed_by": who.strip(), "confirmed_at": stamp}
    if question and question.strip() != scoped.question:
        update |= {"status": "edited", "question": question.strip()}
    confirmed = ScopedQuestion.model_validate(scoped.model_dump() | update)
    write_scope(run_dir, confirmed)
    return confirmed


# ── graph nodes ──────────────────────────────────────────────────────────────────────────────────────


def scope_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        topic = deps.spec.topic
        scoped = None
        for _ in range(MAX_ATTEMPTS):
            reply = deps.generator.generate(SCOPE_SYSTEM, scope_prompt(deps), component="p3.scope")
            scoped = parse_scope(reply, topic.id)
            if scoped is not None:
                break
        if scoped is None:
            return _stop("scope", "the model's reply had no usable scoped question")
        write_scope(deps.run_dir, scoped)
        artifact = _write_json(deps, "scope", scoped.model_dump(mode="json"))
        return {"scope": scoped.model_dump(mode="json"), "artifacts": {"scope_raw": artifact}, "trail": ["scope"]}

    return node


def scope_gate_node(deps: LitDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        scoped = ScopedQuestion.model_validate(state["scope"])
        question, material = questions.question_scoped(deps.spec.topic.text, scoped)
        verdict, confident = ask_gate(deps, "scope", question, material, None, state)
        passed = confident and verdict.answer is True
        artifact = state["artifacts"]["scope_raw"]
        decision = "accept" if passed else "reject"
        sr = stage_result(deps, "scope", artifact, verdict, decision, {"confidence": verdict.confidence})
        update = {"verdicts": {"question_scoped": verdict.model_dump(mode="json")}, "stage_results": [sr],
                  "artifacts": {"scope": artifact}, "trail": ["scope_gate"]}  # fmt: skip
        if not passed:
            why = "the judge was not confident" if not confident else "the judge found the question not specific enough"
            update |= _stop("scope", f"gate: the scoped question was rejected ({why})")
        return update

    return node


def confirm_node(deps: LitDeps) -> Callable[[dict], dict]:
    """The first node after the pause: stops the run unless the user's confirmation is on record (fail closed)."""

    def node(state: dict) -> dict:
        scoped = read_scope(deps.run_dir)
        if scoped is None or scoped.status == "proposed":
            return _stop("scope", "awaiting confirmation: the scoped question has not been confirmed")
        return {"scope": scoped.model_dump(mode="json"), "trail": ["confirm"]}

    return node
