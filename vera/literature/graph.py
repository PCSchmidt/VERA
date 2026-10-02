"""The topic graph: scope -> scope_gate, a pause for the user's confirmation, then the stages that follow.

    scope ─► scope_gate ─► (pause: scripts/confirm_scope.py) ─► confirm ─► [later stages] ─► END

The graph is compiled to interrupt after `scope_gate`. `start_topic_run` runs up to the pause with the budget capped at
the scoping cap, writes a best-so-far report that says the run is awaiting confirmation, and returns. After the user has
confirmed (or edited) the question, `continue_topic_run` restores what was spent, lifts the cap to the run's budget and
resumes from the checkpoint: completed nodes and their ledger records are not repeated. The `confirm` node refuses to
let any later stage run unless the confirmation is on record, even if the graph is resumed some other way.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from vera.graph import resume, run, run_config, sqlite_checkpointer
from vera.literature import scoping, stages, synthesis_stage
from vera.literature.deps import LitDeps
from vera.loop.graph import restore_budget, tracked
from vera.loop.stages import _merge
from vera.loop.stop import guard_stage, route_after, write_best_so_far

NodeFactory = Callable[[LitDeps], Callable[[dict], dict]]
PAUSE_AFTER = "scope_gate"

CORE_NODES: list[tuple[str, str, NodeFactory]] = [  # (node name, stage it belongs to, factory)
    ("scope", "scope", scoping.scope_node),
    ("scope_gate", "scope", scoping.scope_gate_node),
    ("confirm", "scope", scoping.confirm_node),
]
# The stages that follow the confirmation, in order; later features append to this list.
STAGE_NODES: list[tuple[str, str, NodeFactory]] = [
    ("queries", "retrieve", stages.queries_node),
    ("retrieve", "retrieve", stages.retrieve_node),
    ("screen", "retrieve", stages.screen_node),
    ("expand", "retrieve", stages.expand_node),
    ("rescreen", "retrieve", stages.rescreen_node),
    ("read", "read", stages.read_node),
    ("read_gate", "read", stages.read_gate_node),
    ("synthesize", "synthesize", synthesis_stage.synthesize_node),
    ("verify", "synthesize", synthesis_stage.verify_node),
]
AWAITING = "awaiting confirmation: run scripts/confirm_scope.py, then continue the run"


class LitState(TypedDict, total=False):
    scope: dict  # the ScopedQuestion
    queries: list  # search queries written from the confirmed question
    records: list  # keys of the retrieved candidates, best ranked first
    kept: list  # keys that passed the relevance screen
    expansion: dict  # the snowballing step: its seeds and how many candidates it added (or why it was skipped)
    passages: int  # evidence passages written to passages.jsonl
    draft: list  # the drafted section: paragraphs of sentences with claims
    section: dict  # the verified LiteratureSection
    read_report: list  # per paper: how it was read (full text or abstract), and why not when it was not
    artifacts: Annotated[dict, _merge]
    verdicts: Annotated[dict, _merge]
    stage_results: Annotated[list, operator.add]
    trail: Annotated[list, operator.add]
    stop: dict | None
    budget: dict


def build_graph(deps: LitDeps, *, checkpointer: Any = None, extra_nodes: list[tuple[str, str, NodeFactory]] = ()):
    nodes = [*CORE_NODES, *extra_nodes]
    g = StateGraph(LitState)
    for name, stage, factory in nodes:
        g.add_node(name, guard_stage(stage, tracked(deps, factory(deps))))
    g.add_edge(START, nodes[0][0])
    for (a, _, _), (b, _, _) in zip(nodes, nodes[1:], strict=False):
        g.add_conditional_edges(a, route_after(b, END), [b, END])
    g.add_edge(nodes[-1][0], END)
    return g.compile(checkpointer=checkpointer, interrupt_after=[PAUSE_AFTER])


def _graph(deps: LitDeps, extra_nodes):
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    return build_graph(deps, checkpointer=sqlite_checkpointer(deps.run_dir / "checkpoints.sqlite"),
                       extra_nodes=extra_nodes)  # fmt: skip


def start_topic_run(deps: LitDeps, *, extra_nodes: list[tuple[str, str, NodeFactory]] = ()) -> dict:
    """Run scoping up to the confirmation pause, spending at most `deps.scope_cap_usd`."""
    full = deps.budget.max_usd
    deps.budget.max_usd = min(full, deps.scope_cap_usd)
    try:
        graph = _graph(deps, extra_nodes)
        thread = deps.spec.run_id
        state = run(graph, {"trail": []}, thread)
        if not state.get("stop") and graph.get_state(run_config(thread)).next:
            state = {**state, "stop": {"stage": "scope", "reason": AWAITING}}  # paused, not failed
    finally:
        deps.budget.max_usd = full
    write_best_so_far(state, deps.spec, deps.budget, deps.run_dir / "best_so_far.json")
    return state


def continue_topic_run(deps: LitDeps, *, extra_nodes: list[tuple[str, str, NodeFactory]] = ()) -> dict:
    """Resume after the user's confirmation, with the run's full budget. Raises if nothing is confirmed."""
    scoped = scoping.read_scope(deps.run_dir)
    if scoped is None or scoped.status == "proposed":
        raise scoping.ScopeNotConfirmedError("the scoped question has not been confirmed (scripts/confirm_scope.py)")
    graph = _graph(deps, extra_nodes)
    thread = deps.spec.run_id
    deps.budget.max_usd = deps.spec.budget.max_usd
    restore_budget(deps, graph.get_state(run_config(thread)).values.get("budget"))
    state = resume(graph, thread)
    write_best_so_far(state, deps.spec, deps.budget, deps.run_dir / "best_so_far.json")
    return state


def rerun_from(deps: LitDeps, node: str, *, extra_nodes: list[tuple[str, str, NodeFactory]] = ()) -> dict:
    """Run again from the checkpoint just before `node`, in the same run: the same directory, ledger and budget, so the
    earlier attempt's verdicts and spend stay on record (`gates.jsonl` and the ledger only ever grow). Use it when a
    stage's code has changed after a stop (retrieval v2); `scoped question confirmed` is kept, not asked again."""
    scoped = scoping.read_scope(deps.run_dir)
    if scoped is None or scoped.status == "proposed":
        raise scoping.ScopeNotConfirmedError("the scoped question has not been confirmed (scripts/confirm_scope.py)")
    graph = _graph(deps, extra_nodes)
    thread = deps.spec.run_id
    target = next((s for s in graph.get_state_history(run_config(thread)) if tuple(s.next) == (node,)), None)
    if target is None:
        raise LookupError(f"no checkpoint of run {thread!r} stands just before node {node!r}")
    deps.budget.max_usd = deps.spec.budget.max_usd
    restore_budget(deps, target.values.get("budget"))
    state = graph.invoke(None, target.config, durability="sync")
    write_best_so_far(state, deps.spec, deps.budget, deps.run_dir / "best_so_far.json")
    return state
