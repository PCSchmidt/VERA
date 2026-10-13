"""Interpretation sections and the inference check (RSH-F-13, AUD-F-11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge
from tests.test_paper_stage import STATS, fenced, run_nodes, script, setup_run
from vera.audit import inference
from vera.literature import paper_interpret
from vera.schemas import PaperDocument, Question, Verdict

CLAIMS = {
    "C1": "DRMiner reported that rationales mined from Jira logs improved LLM-based repair. (source: DRMiner)",
    "C2": "Failed trajectories are longer and vary more than successful ones. (source: Agent behaviour)",
    "C3": "LLM ensembles lag IR methods in precision for traceability, at 0.42 precision. (source: Beyond Retrieval)",
}


@pytest.mark.parametrize(
    "text, premises, expected",
    [
        ("Trajectory length may signal failure.", ["C2"], None),
        ("Trajectory length may signal failure.", [], "no premise"),
        ("Trajectory length may signal failure.", ["C9"], "does not exist"),
        ("Trajectory length may signal failure [R2].", ["C2"], "cites a source directly"),
        ("As Smith et al. show, length signals failure.", ["C2"], "cites a source directly"),
        ("SWE-agent trajectories may signal failure.", ["C2"], "names SWE-agent"),
        ("Mined rationale, as DRMiner shows, can help repair.", ["C1"], None),
        ("Traceability precision of 0.42 leaves room to improve.", ["C3"], None),
        ("Traceability precision of 0.57 leaves room to improve.", ["C3"], "states 0.57"),
        ("LLMs lag in precision (C3).", ["C3"], None),  # an acronym is not a name; the premise marker is not a number
    ],
)
def test_RSH_F_13_deterministic_rules(text: str, premises: list[str], expected: str | None) -> None:
    problem = inference.statement_problem(text, premises, CLAIMS)
    assert (problem is None) if expected is None else (expected in problem)


def verdict(answer: bool, confidence: float = 0.9) -> tuple[Verdict, bool]:
    v = Verdict(question_id="paper.inference_follows", answer=answer, confidence=confidence,
                confidence_source="self_report", backend="fake", escalated=False, cost_usd=0.0, latency_ms=1,
                trace_id="t", judge_id="p2.judge")  # fmt: skip
    return v, confidence >= 0.7


def test_AUD_F_11_the_audit_fails_a_no_and_warns_an_unsure_verdict() -> None:
    inferences = [
        {
            "id": "I1",
            "section": "Discussion",
            "text": "Length may signal failure.",
            "premises": ["C2"],
            "status": "pass",
        },
        {"id": "I2", "section": "Discussion", "text": "Length proves failure.", "premises": ["C2"], "status": "pass"},
        {"id": "I3", "section": "Conclusions", "text": "Maybe.", "premises": ["C2"], "status": "pass"},
        {"id": "I4", "section": "Conclusions", "text": "Removed one.", "premises": [], "status": "removed"},
    ]
    answers = {"Length may signal failure.": verdict(True), "Length proves failure.": verdict(False),
               "Maybe.": verdict(True, 0.5)}  # fmt: skip

    def ask(q: Question, material: str) -> tuple[Verdict, bool]:
        return answers[material.rsplit("Statement: ", 1)[1]]

    findings = inference.audit(inferences, CLAIMS, ask)
    assert [(f.claim_ids, f.severity, f.check) for f in findings] == [
        (["I2"], "fail", "inference"), (["I3"], "warn", "inference")
    ]  # fmt: skip


class InterpretJudge(LitJudge):
    """Says no to any statement containing PROVES, is unsure about MAYBE, yes otherwise."""

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        out = super().ask(state, questions)
        tail = state.rsplit("Statement: ", 1)[-1]
        return [v.model_copy(update={"answer": "PROVES" not in tail, "confidence": 0.5 if "MAYBE" in tail else 0.9})
                for v in out]  # fmt: skip


def finished_paper(tmp_path: Path, judge=None):
    run, deps = setup_run(tmp_path, judge=judge)
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    assert not state.get("stop")
    return run, deps, state


ABSTRACT = " ".join(["This review paper finds that the sources leave much open about the question it asks."] * 3)


def interpret(deps, state: dict, statements: list, repair: str | None = "[]", abstract: str = ABSTRACT) -> dict:
    replies = [fenced({"sections": statements}), *([repair] if repair is not None else []), abstract, abstract]
    deps.generator.replies["p3.paper.interpret"] = replies
    return paper_interpret.interpret_node(deps)(state)


def test_RSH_F_13_statements_that_fail_are_removed_and_kept_on_record(tmp_path: Path) -> None:
    run, deps, state = finished_paper(tmp_path, judge=InterpretJudge())
    statements = [
        {"heading": "Discussion", "statements": [
            {"text": "Several kinds of information appear recoverable.", "premises": ["C1", "C2"]},
            {"text": "This PROVES traces are enough.", "premises": ["C1"]},
            {"text": "MAYBE more.", "premises": ["C2"]},
            {"text": "An orphan.", "premises": ["C99"]},
        ]},
        {"heading": "Conclusions", "statements": [{"text": "The sources leave much open.", "premises": ["C3"]}]},
        {"heading": "Not a section", "statements": [{"text": "Ignored.", "premises": ["C1"]}]},
    ]  # fmt: skip
    update = interpret(deps, state, statements)
    doc = PaperDocument.model_validate(update["paper"])
    status = {i.text: i.status for i in doc.inferences}
    assert status == {
        "Several kinds of information appear recoverable.": "pass", "This PROVES traces are enough.": "removed",
        "MAYBE more.": "removed", "An orphan.": "removed", "The sources leave much open.": "pass",
    }  # fmt: skip
    md = (run / "paper" / "paper.md").read_text(encoding="utf-8")
    assert "Several kinds of information appear recoverable (C1, C2)." in md and "PROVES" not in md
    assert md.count(paper_interpret.LABEL) == 2  # Discussion and Conclusions; no agenda statement survived
    headings = [s.heading for s in doc.sections]
    assert headings[0] == "Abstract" and headings[-1] == "Threats to validity"
    assert headings.index("Discussion") > headings.index("Method")
    rows = [json.loads(ln) for ln in (run / "paper" / "inferences.jsonl").read_text("utf-8").splitlines()]
    assert len(rows) == 5 and {r["reason"] for r in rows if r["status"] == "removed"} >= {"judge_unsure"}


def test_RSH_F_13_the_interpretation_writer_never_sees_a_passage(tmp_path: Path) -> None:
    run, deps, state = finished_paper(tmp_path)
    prompts: list[str] = []
    generate = deps.generator.generate

    def spy(system: str, prompt: str, *, component: str) -> str:
        if component == "p3.paper.interpret":
            prompts.append(prompt)
        return generate(system, prompt, component=component)

    deps.generator.generate = spy
    interpret(deps, state, [{"heading": "Discussion", "statements": [{"text": "x", "premises": ["C1"]}]}], repair=None)
    passages = [json.loads(ln) for ln in (run / "paper" / "passages.jsonl").read_text("utf-8").splitlines()]
    for prompt in prompts:
        assert "Evidence:" not in prompt and "passage_id" not in prompt
        for p in passages:  # the writer is shown claims, never the passages they were checked against
            assert p["text"] not in prompt and f"<{p['id']}>" not in prompt


def test_RSH_F_13_an_abstract_that_adds_a_fact_twice_is_replaced_by_a_plain_one(tmp_path: Path) -> None:
    run, deps, state = finished_paper(tmp_path)
    adds = "Traces raise repair rates by 87 percent. " + ABSTRACT
    update = interpret(deps, state, [], repair=None, abstract=adds)
    doc = PaperDocument.model_validate(update["paper"])
    assert doc.sections[0].heading == "Abstract" and "87" not in doc.sections[0].text
    assert doc.sections[0].text.startswith("This review paper asks:")
    assert update["stage_results"][0]["metrics"]["abstract_by_model"] == 0.0
