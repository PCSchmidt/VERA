"""LangGraph helpers: a judge `Question` as a node, routing on its `Verdict`, and checkpointing.

JDG-F-05 (node and conditional-edge helpers) and FND-F-02 (checkpoint after
every node, resume after a crash). This is also the evidence for trade T2:
plain LangGraph supplies the graph and the checkpoints; the helpers add the
Meridian-style gate semantics on top:

- `judge_node` asks one question of a judge (a `JudgeBackend` or a `Router`)
  about the state's material, and stamps the verdict with the state's
  `producer_id`, so a judge grading its own producer's work raises
  `SelfGradingError` (no self-grading) instead of routing on it;
- `route_on_verdict` routes on the verdict's answer, and sends a verdict
  below `min_confidence`, a malformed one, or an answer with no route to
  `on_low` (fail closed: an unclear gate never counts as a pass);
- `sqlite_checkpointer` persists checkpoints; `run` and `resume` write one
  synchronously after every node (LangGraph's default is asynchronous, which
  a killed process can lose), so a crashed run continues from its last
  completed node and completed nodes, their model calls and ledger records
  are not repeated.

Graph state is a dict (`JudgedState`). Verdicts are stored as JSON dicts, so
checkpoints hold plain data.
"""

from __future__ import annotations

import operator
import sqlite3
from collections.abc import Callable, Hashable, Mapping
from pathlib import Path
from typing import Annotated, Any, Protocol, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

from vera.schemas import Question, SelfGradingError, Verdict


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


class JudgedState(TypedDict, total=False):
    material: str  # what the judge reads (a result table, a draft, ...)
    producer_id: str | None  # component that produced the material
    verdicts: Annotated[dict[str, dict], _merge]  # question id -> Verdict (JSON)
    trail: Annotated[list[str], operator.add]  # nodes completed, in order


class Judge(Protocol):
    def ask(self, state: str, questions: list[Question]) -> list[Verdict]: ...


def judge_node(question: Question, judge: Judge, *, material_key: str = "material") -> Callable[[dict], dict]:
    """A node that asks `question` about `state[material_key]` and records the Verdict under its id."""

    def node(state: dict) -> dict:
        (verdict,) = judge.ask(state[material_key], [question])
        producer = state.get("producer_id")
        if producer is not None and verdict.judge_id == producer:
            raise SelfGradingError(f"{question.id}: judge {verdict.judge_id!r} produced the material it judges")
        stamped = verdict.model_copy(update={"producer_id": producer})
        return {"verdicts": {question.id: stamped.model_dump(mode="json")}, "trail": [f"judge:{question.id}"]}

    return node


def verdict_of(state: Mapping[str, Any], question_id: str) -> Verdict | None:
    raw = (state.get("verdicts") or {}).get(question_id)
    return Verdict.model_validate(raw) if raw is not None else None


def route_on_verdict(
    question_id: str, routes: Mapping[Hashable, str], *, on_low: str, min_confidence: float = 0.0
) -> Callable[[dict], str]:
    """A conditional-edge function: the node for the verdict's answer, else `on_low` (fail closed)."""

    def route(state: dict) -> str:
        v = verdict_of(state, question_id)
        if v is None or v.confidence_source == "none" or v.confidence < min_confidence:
            return on_low
        for answer, target in routes.items():
            if type(answer) is type(v.answer) and answer == v.answer:  # True must not match 1
                return target
        return on_low

    return route


def add_gate(
    builder: StateGraph,
    name: str,
    question: Question,
    judge: Judge,
    routes: Mapping[Hashable, str],
    *,
    on_low: str,
    min_confidence: float = 0.0,
) -> None:
    """Add a judge node `name` and route out of it on its verdict."""
    builder.add_node(name, judge_node(question, judge))
    targets = sorted(set(routes.values()) | {on_low})
    builder.add_conditional_edges(
        name, route_on_verdict(question.id, routes, on_low=on_low, min_confidence=min_confidence), targets
    )


def sqlite_checkpointer(path: Path) -> SqliteSaver:
    """A checkpointer that survives the process: every completed node is saved to `path`."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def run_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def run(graph: Any, state: dict, thread_id: str) -> dict:
    """Start a run, checkpointing synchronously after every node (FND-F-02)."""
    return graph.invoke(state, run_config(thread_id), durability="sync")


def resume(graph: Any, thread_id: str) -> dict:
    """Continue a run from its last checkpoint (completed nodes are not run again)."""
    return graph.invoke(None, run_config(thread_id), durability="sync")
