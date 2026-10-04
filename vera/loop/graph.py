"""The loop graph: baseline -> ideas -> subset experiments, each stage a producer node then a gate node.

    baseline ─► baseline_gate ─► ideate ─► screen ─► subset_exp ─► results_gate ─► protocol (if registered)
        ─► write_up ─► writeup_gate ─► audit ─► END

After every node a `stop` in the state (a rejected gate, an unsure judge, an exhausted budget) routes straight to
END, so no later stage starts on an unaccepted result (RSH-F-02). Nodes are wrapped with `guard_stage`, so a budget
that would be crossed ends the run cleanly with a best-so-far report instead of an exception.

`run_loop` runs or resumes the graph with the SQLite checkpointer and synchronous checkpoints (T2, FND-F-02), then
writes `best_so_far.json` in the run directory (RSH-F-06). Later features append nodes through `extra_nodes`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from vera.graph import resume, run, run_config, sqlite_checkpointer
from vera.loop import ablation, audit_stage, protocol_stage, stages, writeup
from vera.loop.stages import LoopDeps, LoopState
from vera.loop.stop import guard_stage, route_after, write_best_so_far

NodeFactory = Callable[[LoopDeps], Callable[[dict], dict]]

CORE_NODES: list[tuple[str, str, NodeFactory]] = [  # (node name, stage it belongs to, factory)
    ("baseline", "baseline", stages.baseline_node),
    ("baseline_gate", "baseline", stages.baseline_gate_node),
    ("ideate", "ideate", stages.ideate_node),
    ("screen", "ideate", stages.screen_node),
    ("subset_exp", "subset_exp", stages.subset_exp_node),
    ("results_gate", "subset_exp", stages.results_gate_node),
    ("protocol", "subset_exp", protocol_stage.protocol_node),
    ("ablation", "subset_exp", ablation.ablation_node),
    ("write_up", "write_up", writeup.write_up_node),
    ("writeup_gate", "write_up", writeup.writeup_gate_node),
    ("audit", "audit", audit_stage.audit_node),
]


def tracked(deps: LoopDeps, node: Callable[[dict], dict]) -> Callable[[dict], dict]:
    """After each node, put the Budget in the state so it is checkpointed with the node's other updates."""

    def wrapper(state: dict) -> dict:
        update = node(state)
        return {**update, "budget": deps.budget.model_dump()} if update else update

    return wrapper


def restore_budget(deps: LoopDeps, snapshot: dict | None) -> None:
    """Bring `deps.budget` back to what a crashed process had spent: the larger of the checkpointed snapshot and
    the ledger's own totals (a node that crashed after its calls but before its checkpoint left only ledger
    records). Elapsed wall time comes from the snapshot, since only model calls are in the ledger."""
    budget = deps.budget
    spent, calls = (snapshot or {}).get("spent_usd", 0.0), (snapshot or {}).get("model_calls_used", 0)
    if deps.ledger is not None:
        records = deps.ledger.records()
        spent, calls = max(spent, sum(r.cost_usd for r in records)), max(calls, len(records))
    budget.spent_usd, budget.model_calls_used = spent, calls
    budget.elapsed_seconds = max(budget.elapsed_seconds, (snapshot or {}).get("elapsed_seconds", 0))


def build_graph(
    deps: LoopDeps,
    *,
    checkpointer: Any = None,
    extra_nodes: list[tuple[str, str, NodeFactory]] = (),
    start_at: str | None = None,
):
    """`start_at` names the first node to run (for runs that begin from a recorded earlier state, e.g. from the
    ideas stage onward with a fixed baseline: the generator comparison)."""
    nodes = [*CORE_NODES, *extra_nodes]
    if start_at is not None:
        nodes = nodes[[name for name, _, _ in nodes].index(start_at) :]
    g = StateGraph(LoopState)
    for name, stage, factory in nodes:
        g.add_node(name, guard_stage(stage, tracked(deps, factory(deps))))
    g.add_edge(START, nodes[0][0])
    for (a, _, _), (b, _, _) in zip(nodes, nodes[1:], strict=False):
        g.add_conditional_edges(a, route_after(b, END), [b, END])
    g.add_edge(nodes[-1][0], END)
    return g.compile(checkpointer=checkpointer)


def run_loop(
    deps: LoopDeps,
    *,
    resume_run: bool = False,
    extra_nodes: list[tuple[str, str, NodeFactory]] = (),
    start_at: str | None = None,
    initial_state: dict | None = None,
    retry_from: str | None = None,
) -> dict:
    """Run (or resume) the loop for `deps.spec`; returns the final state. The run directory holds everything."""
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    checkpointer = sqlite_checkpointer(deps.run_dir / "checkpoints.sqlite")
    graph = build_graph(deps, checkpointer=checkpointer, extra_nodes=extra_nodes, start_at=start_at)
    thread = deps.spec.run_id
    if resume_run:
        snapshot = graph.get_state(run_config(thread)).values.get("budget")
        restore_budget(deps, snapshot)
        if retry_from:  # clear a stop so the run continues after `retry_from` (its results are kept as they are)
            graph.update_state(run_config(thread), {"stop": None}, as_node=retry_from)
        state = resume(graph, thread)
    else:
        state = run(graph, initial_state or {"trail": []}, thread)
    write_best_so_far(state, deps.spec, deps.budget, deps.run_dir / "best_so_far.json")
    return state
