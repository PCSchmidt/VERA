"""A paper made from a finished review through the real graph (RSH-F-12, APP-F-04): extend, cap, stop and resume."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests.lit_fakes import LitGenerator, LitJudge, make_lit_spec
from tests.test_paper_evidence import Fetch, make_review, parse
from tests.test_paper_interpret import ABSTRACT
from tests.test_paper_stage import STATS, THEMES, fenced, section, sentences_on
from vera.app import pipeline
from vera.app.appbudget import STOP_FILE, AppBudget
from vera.ledger import Ledger
from vera.literature import paper_evidence
from vera.literature.deps import LitDeps
from vera.schemas import PaperRequest

REVIEW_FILES = [
    "retrieved.jsonl",
    "passages.jsonl",
    "literature.md",
    "artifacts/reading.json",
    "artifacts/queries.json",
]


def make_deps(tmp_path: Path, review: Path) -> LitDeps:
    spec = make_lit_spec("paper-run")
    run_dir = tmp_path / "run"
    budget = AppBudget(**spec.budget.model_dump()).watch(run_dir)
    ledger = Ledger(tmp_path / "run_paper-run.jsonl", run_id="paper-run")
    (review / "literature.md").write_text(
        "## Literature review\n\nA review [R1].\n\n## References\n\n[R1] x\n", "utf-8"
    )
    deps = LitDeps(spec=spec, generator=LitGenerator(ledger, budget), judge=LitJudge(ledger, budget), budget=budget,
                   run_dir=run_dir, ledger=ledger)  # fmt: skip

    def finished_review(deps: LitDeps):
        def node(state: dict) -> dict:  # stands in for the review's stages: leaves a finished review's files
            for rel in REVIEW_FILES:
                (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(review / rel, run_dir / rel)
            return {"section": {"retrieval_stats": STATS}, "trail": ["verify"]}

        return node

    deps.extra |= {"fetch_pdf": Fetch(), "parse_pdf": parse, "review_node": ("verify", "synthesize", finished_review)}
    return deps


def finish_review(deps: LitDeps, monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "STAGE_NODES", [deps.extra["review_node"]])
    pipeline.run_phase(deps, "start")
    pipeline.confirm(deps.run_dir, None)
    done = pipeline.run_phase(deps, "continue")
    assert not done.get("stop") and done["trail"][-1] == "verify"


def script(deps: LitDeps) -> None:
    """Replies for the outline and the sections, from the passages the paper's wider reading will produce."""
    scratch = deps.run_dir.parent / "scratch"
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.copytree(deps.run_dir, scratch, ignore=shutil.ignore_patterns("checkpoints.sqlite*", "paper"))
    paper_evidence.widen(scratch, Fetch(), parse)
    passages = [json.loads(ln) for ln in (scratch / "paper" / "passages.jsonl").read_text("utf-8").splitlines() if ln]
    replies = [fenced({"title": "Agent traces: a review", "themes": THEMES}),
               section(sentences_on(passages, "agent traces trajectory")[:3])]  # fmt: skip
    replies += [section(sentences_on(passages, t["focus"])[:6]) for t in THEMES[:3]]
    deps.generator.replies["p3.paper.write"] = replies + ["[]"]
    discussion = {"heading": "Discussion", "statements": [{"text": "The sources leave much open.", "premises": ["C1"]}]}
    deps.generator.replies["p3.paper.interpret"] = [fenced({"sections": [discussion]}), ABSTRACT]


def test_RSH_F_12_a_paper_extends_a_finished_review_in_the_same_run(tmp_path: Path, monkeypatch) -> None:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    spent_before = sum(r.cost_usd for r in deps.ledger.records())
    script(deps)
    state = pipeline.run_paper(deps, PaperRequest(max_usd=0.5))
    assert not state.get("stop"), state.get("stop")
    assert state["trail"][-5:] == ["paper_widen", "paper_outline", "paper_write", "paper_verify", "paper_interpret"]
    doc = json.loads((deps.run_dir / "paper" / "paper.json").read_text("utf-8"))
    assert [s["kind"] for s in doc["sections"]][:3] == ["summary", "evidence", "record"]
    assert any(s["kind"] == "interpretation" for s in doc["sections"])
    assert (deps.run_dir / "paper" / "paper.md").exists()
    assert deps.generator.calls.count("p3.scope") == 1  # the review was not repeated
    assert abs(deps.budget.max_usd - (spent_before + 0.5)) < 1e-9  # the paper's own cap, on top of the review's spend
    assert json.loads((deps.run_dir / "paper" / "request.json").read_text("utf-8"))["max_usd"] == 0.5


def test_APP_F_04_a_stopped_paper_resumes_from_its_checkpoint(tmp_path: Path, monkeypatch) -> None:
    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    spent_before = sum(r.cost_usd for r in deps.ledger.records())
    script(deps)
    (deps.run_dir / STOP_FILE).write_text("stop", encoding="utf-8")  # the user pressed Stop before the outline
    stopped = pipeline.run_paper(deps, PaperRequest(max_usd=0.5))
    assert stopped["stop"]["stage"] == "paper" and "stopped by the user" in stopped["stop"]["reason"]
    widened = (deps.run_dir / "paper" / "passages.jsonl").read_text("utf-8")
    script(deps)  # the stopped call consumed its scripted reply; give the writer its script again
    done = pipeline.resume_paper(deps, PaperRequest(max_usd=0.5), spent_before)
    assert not done.get("stop"), done.get("stop")
    assert (deps.run_dir / "paper" / "paper.md").exists()
    assert (deps.run_dir / "paper" / "passages.jsonl").read_text("utf-8") == widened
    assert done["trail"].count("paper_widen") == 1  # the widening that had finished was not run again


def test_AUD_F_11_the_paper_audit_checks_claims_and_re_checks_interpretation(tmp_path: Path, monkeypatch) -> None:
    from tests.test_paper_interpret import InterpretJudge  # noqa: PLC0415

    deps = make_deps(tmp_path, make_review(tmp_path / "review", n_papers=8))
    finish_review(deps, monkeypatch)
    script(deps)
    assert not pipeline.run_paper(deps, PaperRequest(max_usd=0.5)).get("stop")
    out = deps.run_dir / "paper"
    assert pipeline.run_paper_audit(deps, judge=InterpretJudge()) == "green"
    report = json.loads((out / "audit_report.json").read_text("utf-8"))
    assert report["checks_run"] == ["citation", "claim_support", "inference", "sentence"]  # +sentence (Increment 7)
    assert "Interpretation statements re-checked: 1" in (out / "audit.md").read_text("utf-8")

    doc = json.loads((out / "paper.json").read_text("utf-8"))  # a statement that does not follow, slipped in later
    doc["inferences"].append({"id": "I9", "section": "Discussion", "text": "This PROVES everything.",
                              "premises": ["C1"], "verdicts": [], "status": "pass", "reason": None})  # fmt: skip
    (out / "paper.json").write_text(json.dumps(doc), encoding="utf-8")
    assert pipeline.run_paper_audit(deps, judge=InterpretJudge()) == "red"
    findings = json.loads((out / "audit_report.json").read_text("utf-8"))["findings"]
    assert [(f["check"], f["claim_ids"]) for f in findings] == [("inference", ["I9"])]
    assert (deps.run_dir / "audit.md").exists() is False or "paper" not in (deps.run_dir / "audit.md").read_text(
        "utf-8"
    )
