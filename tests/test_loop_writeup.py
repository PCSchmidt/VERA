"""RSH-F-07: the write-up follows the output guidance and the final check enforces it. Offline."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from tests.loop_fakes import GUIDANCE, REFS, FakeJudge, make_deps, paper
from vera.loop import references, tables
from vera.loop.graph import run_loop
from vera.loop.writeup import assemble, check_guidance, word_count
from vera.schemas import OutputGuidance, StageResult

SECTIONS = ("Abstract", "Method", "Results", "Limitations")


def final_decision(state: dict) -> str:
    return next(StageResult.model_validate(s).decision for s in state["stage_results"] if s["stage"] == "write_up")


# ── the deterministic checks ─────────────────────────────────────────────────────────────────────────


def test_RSH_F_07_a_compliant_draft_passes_the_checks() -> None:
    assert check_guidance(assemble_for_check(paper()), GUIDANCE, REFS) == []


def assemble_for_check(draft: str) -> str:
    return draft.replace("[[RESULTS_TABLE]]", "| table |") + "\n\n## References\n\n[R1] x\n[R2] y\n"


@pytest.mark.parametrize(
    ("draft", "expect"),
    [
        (paper(words=900), "too long"),  # over the 400-word limit
        (paper(sections=("Abstract", "Method", "Results")), "missing required section: Limitations"),
        (paper(extra="\nThis reaches the state of the art on everything.\n"), "forbidden content"),
        (paper(extra="\nSee also [R9].\n"), "cites records that were not retrieved: ['R9']"),
    ],
)
def test_RSH_F_07_each_guidance_violation_is_found(draft: str, expect: str) -> None:
    problems = check_guidance(assemble_for_check(draft), GUIDANCE, REFS)
    assert any(expect in p for p in problems), problems


def test_RSH_F_07_forbidden_phrases_match_case_insensitively_and_other_constraints_are_left_to_the_judge() -> None:
    g = OutputGuidance(constraints=["forbid: Breakthrough", "write for a general audience"])
    assert check_guidance("A BREAKTHROUGH result.", g, REFS) == ["contains forbidden content: 'Breakthrough'"]
    assert check_guidance("A result.", g, REFS) == []  # the free-text constraint is not a program's to judge


def test_RSH_F_07_word_count_ignores_markup() -> None:
    assert word_count("## Title\n\nOne two three. Four-five.") == 5


# ── the stage, end to end ────────────────────────────────────────────────────────────────────────────


def test_RSH_F_07_a_compliant_write_up_is_accepted_and_its_numbers_come_from_the_logs(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    state = run_loop(deps)
    assert state.get("stop") is None and final_decision(state) == "accept"
    text = (deps.run_dir / "paper.md").read_text(encoding="utf-8")
    results = json.loads((deps.run_dir / "artifacts" / "results.json").read_text(encoding="utf-8"))
    # every number in the table is the rendered mean or std of a value in results.json
    allowed = set()
    for res in results["results"].values():
        for d in results["datasets"]:
            for key, _ in tables.METRICS:
                allowed |= {tables.fmt_sig(res[d][key]["mean"]), tables.fmt_sig(res[d][key]["std"], 2)}
    rows = [ln for ln in text.splitlines() if ln.startswith("|") and "±" in ln]
    assert rows
    for row in rows:
        for mean, std in re.findall(r"([\d.]+) ± ([\d.]+)", row):
            assert mean in allowed and std in allowed, (mean, std)
    assert text.count("| Method |") == 1  # the table VERA rendered, once


def test_RSH_F_07_the_reference_list_is_built_from_retrieved_records_not_from_the_model(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(extra="\n## References\n\n[R1] Invented, A. A paper that does not exist. 2024.\n")]
    run_loop(deps)
    text = (deps.run_dir / "paper.md").read_text(encoding="utf-8")
    assert "Invented" not in text and text.count("## References") == 1
    for rec in REFS:
        assert references.format_reference(rec) in text


def test_RSH_F_07_a_violating_draft_is_regenerated_once_with_the_problems_listed(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(words=900), paper()]  # too long, then fine
    state = run_loop(deps)
    assert final_decision(state) == "accept"
    assert deps.generator.calls.count("p3.write_up") == 2


def test_RSH_F_07_a_draft_that_still_violates_is_rejected_by_the_gate_and_stops_the_run(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(words=900)]  # every attempt too long
    state = run_loop(deps)
    assert final_decision(state) == "reject" and deps.generator.calls.count("p3.write_up") == 2
    assert state["stop"]["stage"] == "write_up" and "too long" in state["stop"]["reason"]
    check = json.loads((deps.run_dir / "artifacts" / "writeup_check.json").read_text(encoding="utf-8"))
    assert check["problems"] and check["shadow"] is False
    report = json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))
    assert "write_up" not in report["stages_completed"]  # a rejected write-up is not "completed"


GUIDANCE_Q = "loop.guidance_met"


class SteadyJudge(FakeJudge):
    """Confident everywhere, except the guidance question, whose confidence is set by the test."""

    def __init__(self, guidance_confidence: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.guidance_confidence = guidance_confidence

    def ask(self, state, questions):
        return [
            v.model_copy(update={"confidence": self.guidance_confidence if v.question_id == GUIDANCE_Q else 0.95})
            for v in super().ask(state, questions)
        ]


@pytest.mark.parametrize(("answer", "confidence", "ok"), [(True, 0.9, True), (False, 0.9, False), (True, 0.3, False)])
def test_RSH_F_07_the_judge_must_confirm_the_guidance_is_met(tmp_path: Path, answer, confidence, ok) -> None:
    deps = make_deps(tmp_path, judge=SteadyJudge(confidence, overrides={"loop.guidance_met": answer}))
    state = run_loop(deps)
    assert (final_decision(state) == "accept") is ok
    assert (state.get("stop") is None) is ok


def test_RSH_F_07_the_judge_cannot_rescue_a_draft_that_fails_the_deterministic_checks(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, judge=FakeJudge(overrides={"loop.guidance_met": True}))
    deps.generator.drafts = [paper(extra="\nthe state of the art\n")]
    state = run_loop(deps)
    assert final_decision(state) == "reject" and "forbidden" in state["stop"]["reason"]


def test_RSH_F_07_the_table_is_inserted_even_when_the_model_forgets_the_token() -> None:
    from tests.loop_fakes import BASELINE_OK, IDEA_RESULTS, make_spec  # noqa: PLC0415
    from vera.loop.stages import LoopDeps  # noqa: PLC0415

    deps = LoopDeps(spec=make_spec(), target={}, generator=None, judge=None, sandbox=None,  # type: ignore[arg-type]
                    budget=make_spec().budget, run_dir=Path("."), data_dir=Path("."))  # fmt: skip
    state = {"results": {tables.BASELINE: BASELINE_OK, "C1: x": IDEA_RESULTS["C1"]}}
    text = assemble("## Abstract\n\nA.\n\n## Results\n\nWe ran it.\n\n## Limitations\n\nB.\n", state, deps, REFS)
    assert text.index("## Results") < text.index("| Method |") < text.index("## Limitations")
    assert text.rstrip().endswith(references.format_reference(REFS[-1]))
    appended = assemble("Just prose.", state, deps, REFS)
    assert "| Method |" in appended


# ── references: retrieved, logged, reused ────────────────────────────────────────────────────────────

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry><id>http://arxiv.org/abs/2510.24815v3</id><published>2025-10-28T00:00:00Z</published>
  <title>Tree Ensemble Explainability
   through the Hoeffding Functional Decomposition</title>
  <author><name>Clement Benard</name></author></entry>
 <entry><id>http://arxiv.org/abs/1603.02754v3</id><published>2016-03-09T00:00:00Z</published>
  <title>XGBoost: A Scalable Tree Boosting System</title>
  <author><name>Tianqi Chen</name></author><author><name>Carlos Guestrin</name></author></entry>
</feed>"""


def test_references_are_retrieved_once_logged_and_reused(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text=ATOM)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    run_dir = tmp_path / "run"
    first = references.retrieve_seed_references(run_dir, fetch=lambda ids: references.fetch_arxiv(ids, client))
    assert [r["key"] for r in first] == ["R1", "R2"]
    assert first[0]["title"] == "Tree Ensemble Explainability through the Hoeffding Functional Decomposition"
    assert first[0]["id"] == "arXiv:2510.24815" and first[1]["authors"] == ["Tianqi Chen", "Carlos Guestrin"]
    assert "id_list=2510.24815%2C1603.02754" in calls[0]
    again = references.retrieve_seed_references(run_dir, fetch=lambda ids: pytest.fail("must reuse the log"))
    assert again == first and (run_dir / "retrieved.jsonl").exists()


def test_references_fail_loudly_when_nothing_is_retrieved(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no records"):
        references.retrieve_seed_references(tmp_path / "run", fetch=lambda ids: [])
    assert not (tmp_path / "run" / "retrieved.jsonl").exists()  # no empty log that later runs would trust


# ── RSH-F-05: the final audit gates success ──────────────────────────────────────────────────────────


def audit_of(deps) -> dict:
    return json.loads((deps.run_dir / "artifacts" / "audit_report.json").read_text(encoding="utf-8"))


def test_RSH_F_05_a_failing_audit_blocks_success_and_the_report_says_why(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(extra="\nC1 lowered the baseline residual by 41% on Analytical.\n")]
    state = run_loop(deps)
    assert state["stop"]["stage"] == "audit" and state["stop"]["reason"].startswith("gate: audit failed")
    assert "41" in state["stop"]["reason"]
    audit = StageResult.model_validate(state["stage_results"][-1])
    assert (audit.stage, audit.decision) == ("audit", "reject")
    assert audit.gate.judge_id != audit.producer_id and audit.gate.question_id == "loop.audit_clean"
    report = json.loads((deps.run_dir / "best_so_far.json").read_text(encoding="utf-8"))
    assert report["stop_reason"].startswith("gate: audit failed") and "audit" not in report["stages_completed"]
    assert audit_of(deps)["overall"] == "red" and (deps.run_dir / "audit.md").exists()
    assert all(f["evidence"] for f in audit_of(deps)["findings"])  # AUD-F-09


def test_RSH_F_05_an_amber_audit_passes_but_states_what_it_could_not_confirm(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    deps.generator.drafts = [paper(extra="\nThe work was supported by grant 5873.4 of an agency.\n")]
    state = run_loop(deps)
    assert state.get("stop") is None and audit_of(deps)["overall"] == "amber"
    assert [f["severity"] for f in audit_of(deps)["findings"]] == ["warn"]
    assert StageResult.model_validate(state["stage_results"][-1]).decision == "accept"


def test_RSH_F_05_a_clean_run_is_green_and_its_audit_judge_calls_are_logged_with_the_writeup_as_producer(
    tmp_path: Path,
) -> None:
    deps = make_deps(tmp_path)
    state = run_loop(deps)
    assert state.get("stop") is None and audit_of(deps)["overall"] == "green"
    assert audit_of(deps)["checks_run"] == ["citation", "numeric"] and "method_code" in audit_of(deps)["checks_skipped"]


def test_RSH_F_05_the_audit_judge_may_not_be_the_writeup_producer(tmp_path: Path) -> None:
    from vera.loop.stages import ask_gate  # noqa: PLC0415
    from vera.schemas import SelfGradingError  # noqa: PLC0415

    deps = make_deps(tmp_path, judge=FakeJudge(overrides={"cite.contains_entry": True}, judge_id="p3.write_up"))
    q = questions_for_audit()
    with pytest.raises(SelfGradingError):
        ask_gate(deps, "audit", q, "material", None, {}, producer="p3.write_up")


def questions_for_audit():
    from vera.schemas import Question, QuestionType  # noqa: PLC0415

    return Question(id="cite.contains_entry", type=QuestionType.BOOLEAN, text="?")
