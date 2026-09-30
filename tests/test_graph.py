"""FND-F-02 (checkpoint and resume after a crash) and JDG-F-05 (graph helpers routing on a Verdict). No network."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vera.graph import route_on_verdict, run, run_config, sqlite_checkpointer
from vera.graph.demo import BEATS, RUNNER_ID, build_demo
from vera.schemas import Question, SelfGradingError, Verdict

WORKER = Path(__file__).with_name("_graph_worker.py")
ROOT = Path(__file__).resolve().parents[1]


def worker(tmp_path: Path, mode: str, crash: bool = False) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(WORKER), str(tmp_path / "ck.sqlite"), str(tmp_path / "ledger.jsonl"), mode]
    return subprocess.run(args + (["--crash"] if crash else []), capture_output=True, text=True, cwd=ROOT,
                          check=False)  # fmt: skip


def ledger_components(tmp_path: Path) -> list[str]:
    lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(ln)["component"] for ln in lines if ln.strip()]


def test_FND_F_02_killed_run_resumes_without_repeating_completed_nodes(tmp_path: Path) -> None:
    killed = worker(tmp_path, "start", crash=True)
    assert killed.returncode == 3, killed.stderr  # died inside node b
    assert ledger_components(tmp_path) == ["node.a"]

    resumed = worker(tmp_path, "resume")
    assert resumed.returncode == 0, resumed.stderr
    assert resumed.stdout.strip() == "a,b,c"  # state carried over from before the crash
    assert ledger_components(tmp_path) == ["node.a", "node.b", "node.c"]  # a was not called again


def test_FND_F_02_uninterrupted_run_checkpoints_every_node(tmp_path: Path) -> None:
    done = worker(tmp_path, "start")
    assert done.returncode == 0 and done.stdout.strip() == "a,b,c"
    again = worker(tmp_path, "resume")  # nothing left to run
    assert again.returncode == 0
    assert ledger_components(tmp_path) == ["node.a", "node.b", "node.c"]


class FakeJudge:
    def __init__(self, answer, confidence: float = 0.9, judge_id: str = "p2.judge", source: str = "self_report"):
        self.answer, self.confidence, self.judge_id, self.source = answer, confidence, judge_id, source
        self.asked: list[str] = []

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        self.asked.append(state)
        return [Verdict(question_id=q.id, answer=self.answer, confidence=self.confidence,
                        confidence_source=self.source, backend="fake", escalated=False, cost_usd=0.0,
                        latency_ms=1, trace_id="t", judge_id=self.judge_id) for q in questions]  # fmt: skip


@pytest.mark.parametrize(
    ("answer", "confidence", "source", "end"),
    [
        (True, 0.9, "self_report", "write_up"),
        (False, 0.95, "logprobs", "next_idea"),
        (True, 0.5, "self_report", "human_review"),  # below min_confidence
        ("", 0.0, "none", "human_review"),  # malformed
    ],
)
def test_JDG_F_05_demo_graph_routes_on_the_verdict(answer, confidence, source, end) -> None:
    judge = FakeJudge(answer, confidence, source=source)
    out = build_demo(judge, "| m | 0.1 |").invoke({"trail": []})
    assert out["trail"] == ["run_candidate", "judge:loop.beats_baseline", end]
    assert judge.asked == ["| m | 0.1 |"]
    v = Verdict.model_validate(out["verdicts"][BEATS.id])
    assert v.producer_id == RUNNER_ID and v.judge_id == "p2.judge"


def test_JDG_F_05_judge_may_not_grade_its_own_producer() -> None:
    with pytest.raises(SelfGradingError):
        build_demo(FakeJudge(True, judge_id=RUNNER_ID), "t").invoke({"trail": []})


def test_JDG_F_05_route_does_not_confuse_true_with_one() -> None:
    v = FakeJudge(1).ask("s", [BEATS])[0]
    route = route_on_verdict(BEATS.id, {True: "yes"}, on_low="low")
    assert route({"verdicts": {BEATS.id: v.model_dump(mode="json")}}) == "low"


def test_FND_F_02_demo_graph_checkpoints_to_sqlite(tmp_path: Path) -> None:
    graph = build_demo(FakeJudge(False), "t", checkpointer=sqlite_checkpointer(tmp_path / "demo.sqlite"))
    run(graph, {"trail": []}, "demo")
    state = graph.get_state(run_config("demo"))
    assert state.values["trail"][-1] == "next_idea" and not state.next
