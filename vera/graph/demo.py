"""Demo graph (JDG-F-05): the Increment 2 loop's "does the result beat the baseline?" gate.

  run_candidate ──► beats_baseline (judge) ──true──► write_up
                                           ──false─► next_idea
                                           ──unclear─► human_review

`run_candidate` stands in for the loop's runner: it puts a result table in the
state as the material, produced by `RUNNER_ID`. The judge must be a different
component; a judge whose id is `RUNNER_ID` raises `SelfGradingError`.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from vera.graph import Judge, JudgedState, add_gate
from vera.schemas import Question, QuestionType

RUNNER_ID = "p3.runner"
BEATS = Question(
    id="loop.beats_baseline",
    type=QuestionType.BOOLEAN,
    text="Does the candidate beat the TreeHFD baseline on the primary metric? Its mean must be strictly better.",
)


def _step(name: str):
    def node(state: dict) -> dict:
        return {"trail": [name]}

    return node


def build_demo(judge: Judge, table: str, *, min_confidence: float = 0.7, checkpointer=None):
    def run_candidate(state: dict) -> dict:
        return {"material": table, "producer_id": RUNNER_ID, "trail": ["run_candidate"]}

    g = StateGraph(JudgedState)
    g.add_node("run_candidate", run_candidate)
    for name in ("write_up", "next_idea", "human_review"):
        g.add_node(name, _step(name))
        g.add_edge(name, END)
    g.add_edge(START, "run_candidate")
    g.add_edge("run_candidate", "beats_baseline")
    add_gate(g, "beats_baseline", BEATS, judge, {True: "write_up", False: "next_idea"},
             on_low="human_review", min_confidence=min_confidence)  # fmt: skip
    return g.compile(checkpointer=checkpointer)
