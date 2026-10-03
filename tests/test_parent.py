"""Parent-problem selection (RSH-F-10): repositories found in papers, checked live, picked or refused with reasons."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge, fenced, make_lit_deps
from vera.literature import parent, scoping
from vera.schemas import ParentCandidate, ParentSelection, StageResult

TEXT = (
    "We release our code at https://github.com/ThalesGroup/treehfd/ for reproducibility. "
    "As a baseline we use https://github.com/other/baseline-lib. See https://github.com/features for more."
)


def test_RSH_F_10_repositories_are_found_in_text_and_links() -> None:
    found = parent.find_repos(TEXT, ["https://github.com/linked/only-in-pdf.git", "https://example.org/x"])
    urls = [f["url"] for f in found]
    assert urls == ["https://github.com/ThalesGroup/treehfd", "https://github.com/other/baseline-lib",
                    "https://github.com/linked/only-in-pdf"]  # fmt: skip
    assert "release our code" in found[0]["context"]  # the sentence that names it, for the model to read


def test_RSH_F_10_a_url_broken_across_lines_is_rejoined() -> None:
    found = parent.find_repos("code: https://github.com/ThalesGroup/\ntreehfd is public", [])
    assert [f["url"] for f in found] == ["https://github.com/ThalesGroup/treehfd"]


def test_RSH_F_10_a_harness_is_matched_by_the_repository_the_dockerfile_builds(tmp_path: Path) -> None:
    (tmp_path / "docker" / "sandbox-x").mkdir(parents=True)
    (tmp_path / "docker" / "sandbox-x" / "Dockerfile").write_text("# https://github.com/ThalesGroup/treehfd at abc\n")
    assert parent.harness_for("https://github.com/ThalesGroup/treehfd", tmp_path) == "docker/sandbox-x"
    assert parent.harness_for("https://github.com/other/thing", tmp_path) is None


def cand(**kw) -> ParentCandidate:
    base = dict(source_key="R1", paper_id="arXiv:1", title="T", repo_url="https://github.com/a/b", repo_resolves=True,
                licence="MIT", own_code="yes", datasets=["airfoil"], compute="CPU", compute_basis="stated",
                cpu_minutes=2.0)  # fmt: skip
    return ParentCandidate(**(base | kw))


def test_RSH_F_10_deterministic_problems_and_ordering() -> None:
    assert parent.problems(cand()) == []
    bad = parent.problems(cand(repo_resolves=False, licence=None, archived=True, own_code="no", datasets=[],
                               cpu_minutes=500))  # fmt: skip
    assert len(bad) == 6
    good = cand(repo_url="https://github.com/a/good")
    worse = cand(repo_url="https://github.com/a/worse", licence=None)
    harnessed = cand(repo_url="https://github.com/a/harness", harness_in_docker="docker/x", cpu_minutes=9.0)
    assert [c.repo_url.rsplit("/", 1)[1] for c in parent.order([worse, good, harnessed])] == [
        "harness",
        "good",
        "worse",
    ]


def test_RSH_F_10_a_selection_picks_or_refuses_not_both_and_not_neither() -> None:
    kw = dict(run_id="r", topic_id="t", question="q?", candidates=[cand()])
    ParentSelection(picked="https://github.com/a/b", **kw)
    ParentSelection(none_fits_reason="nothing runs on CPU", **kw)
    with pytest.raises(ValueError):
        ParentSelection(**kw)
    with pytest.raises(ValueError):
        ParentSelection(picked="https://github.com/a/b", none_fits_reason="x", **kw)
    with pytest.raises(ValueError):
        ParentSelection(picked="https://github.com/not/listed", **kw)


# ── the nodes ────────────────────────────────────────────────────────────────────────────────────────

ASSESS = [{"index": 0, "own_code": "yes", "datasets": ["airfoil"], "compute": "xgboost, CPU",
           "compute_basis": "inferred", "cpu_minutes": 1.5, "notes": "the paper's own package"},
          {"index": 1, "own_code": "no", "datasets": [], "compute": "", "compute_basis": "unknown",
           "cpu_minutes": None, "notes": "a baseline library"}]  # fmt: skip


def setup(tmp_path: Path, monkeypatch, *, empirical: bool = True, assess=ASSESS, lookup=None, judge=None):
    deps = make_lit_deps(tmp_path, replies={"p3.parent": fenced(assess) if assess is not None else "no json"})
    if judge:
        deps.judge = judge(deps)
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    rec = {"key": "R1", "title": "TreeHFD", "authors": ["C. Benard"], "year": "2025", "id": "arXiv:2510.24815",
           "url": "https://arxiv.org/abs/2510.24815", "source": "arxiv", "abstract": "A method.",
           "pdf_url": "https://arxiv.org/pdf/2510.24815"}  # fmt: skip
    (deps.run_dir / "retrieved.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    scoped = scoping.ScopedQuestion(
        topic_id="t-a",
        question="q?",
        why_researchable="w",
        empirical=empirical,
        status="confirmed",
        confirmed_by="Chris",
        confirmed_at="2026-10-03T10:00:00Z",
    )
    scoping.write_scope(deps.run_dir, scoped)
    deps.extra["fetch_pdf"] = lambda url: b"%PDF fake"
    deps.extra["repo_lookup"] = lookup or (lambda url: {"resolves": True, "licence": "MIT", "pushed_at": "2026-01-01"})
    deps.extra["root"] = tmp_path
    monkeypatch.setattr(parent, "pdf_text_and_links", lambda pdf: (TEXT, []))
    return deps


def run_nodes(deps) -> dict:
    state = {"read_report": [{"key": "R1", "mode": "fulltext"}]}
    state |= parent.parent_node(deps)(state)
    return state | parent.parent_gate_node(deps)(state)


def test_RSH_F_10_the_stage_picks_the_papers_own_repository(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch)
    state = run_nodes(deps)
    sel = ParentSelection.model_validate_json((deps.run_dir / "parent.json").read_text(encoding="utf-8"))
    assert state["parent"] == "https://github.com/ThalesGroup/treehfd" == sel.picked
    assert [c.own_code for c in sel.candidates] == ["yes", "no"]
    assert sel.candidates[0].compute_basis == "inferred"
    sr = StageResult.model_validate(state["stage_results"][0])
    assert sr.stage == "parent" and sr.decision == "accept" and sr.gates[0].question_id == "lit.parent_fits"


def test_RSH_F_10_no_repository_means_a_checked_refusal(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch, lookup=lambda url: {"resolves": False})
    state = run_nodes(deps)
    sel = ParentSelection.model_validate_json((deps.run_dir / "parent.json").read_text(encoding="utf-8"))
    assert sel.picked is None and "does not resolve" in sel.none_fits_reason
    assert [v.question_id for v in sel.verdicts] == ["lit.parent_refusal"]  # the refusal went to the judge
    assert state["stage_results"][0]["decision"] == "accept"


def test_RSH_F_10_a_refusal_the_judge_doubts_stops_the_run(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch, lookup=lambda url: {"resolves": False},
                 judge=lambda d: LitJudge(d.ledger, d.budget, answers={"lit.parent_refusal": False}))  # fmt: skip
    state = run_nodes(deps)
    assert state["stop"]["stage"] == "parent" and state["stage_results"][0]["decision"] == "reject"


def test_RSH_F_10_a_judge_no_moves_on_and_then_refuses(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch, judge=lambda d: LitJudge(d.ledger, d.budget,
                                                                 answers={"lit.parent_fits": False}))  # fmt: skip
    state = run_nodes(deps)
    assert state["parent"] is None
    sel = ParentSelection.model_validate_json((deps.run_dir / "parent.json").read_text(encoding="utf-8"))
    assert "the judge did not accept it" in sel.none_fits_reason


def test_RSH_F_10_a_non_empirical_question_needs_no_parent_and_asks_nothing(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch, empirical=False)
    state = run_nodes(deps)
    assert "stage_results" not in state and state["parent"] is None
    assert deps.judge.asked == [] and deps.generator.calls == []
    sel = ParentSelection.model_validate_json((deps.run_dir / "parent.json").read_text(encoding="utf-8"))
    assert "not empirical" in sel.none_fits_reason


def test_RSH_F_10_unreadable_model_output_leaves_candidates_unassessed_and_refused(tmp_path: Path, monkeypatch) -> None:
    deps = setup(tmp_path, monkeypatch, assess=None)
    state = run_nodes(deps)
    sel = ParentSelection.model_validate_json((deps.run_dir / "parent.json").read_text(encoding="utf-8"))
    assert sel.picked is None and all(c.compute_basis == "unknown" for c in sel.candidates)
    assert "no public dataset identified" in sel.none_fits_reason
    assert state["stage_results"][0]["decision"] == "accept"


def test_RSH_F_10_the_model_reads_the_sentences_about_datasets_and_compute() -> None:
    text = (
        "We study many things in this paper. Experiments use the UCI Airfoil and Concrete datasets, "
        "each with fewer than two thousand rows. Training takes a few seconds on one CPU core. "
        "The weather was pleasant during the writing of this paper."
    )
    ex = parent.evidence_excerpt(text)
    assert "Airfoil" in ex and "seconds on one CPU" in ex and "weather" not in ex
    item = {"title": "T", "paper_id": "arXiv:1", "repo_url": "https://github.com/a/b", "url_context": "c",
            "abstract": "abs", "excerpt": ex}  # fmt: skip
    assert "Airfoil" in parent.assess_prompt("q?", [item])
