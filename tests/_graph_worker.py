"""Subprocess worker for the FND-F-02 kill-and-resume test (not a test module).

Runs a three-node graph (a -> b -> c); each node makes one metered fake
model call, so the ledger shows which nodes ran. With --crash, the process
dies (os._exit, no cleanup) on entering node b, as a killed run would.

Usage: python _graph_worker.py <db> <ledger> start|resume [--crash]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from vera.graph import JudgedState, resume, run, sqlite_checkpointer
from vera.ledger import CallResult, Ledger, metered_call
from vera.schemas import Budget


def main() -> None:
    db, ledger_path, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    crash = "--crash" in sys.argv
    ledger = Ledger(ledger_path, run_id="graph")
    budget = Budget(max_usd=1.0, max_wall_seconds=600)

    def step(name: str):
        def node(state: dict) -> dict:
            if crash and name == "b":
                os._exit(3)
            metered_call(lambda: CallResult(text=name, model="fake", input_tokens=1, output_tokens=1, cost_usd=0.001),
                         ledger=ledger, budget=budget, component=f"node.{name}", backend="fake", model="fake",
                         estimate_usd=0.001)  # fmt: skip
            return {"trail": [name]}

        return node

    g = StateGraph(JudgedState)
    for name in "abc":
        g.add_node(name, step(name))
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", END)
    graph = g.compile(checkpointer=sqlite_checkpointer(db))
    out = run(graph, {"trail": []}, "t1") if mode == "start" else resume(graph, "t1")
    print(",".join(out["trail"]))


if __name__ == "__main__":
    main()
