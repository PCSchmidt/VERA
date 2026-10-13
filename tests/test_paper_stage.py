"""The paper stage (RSH-F-12): outline, evidence sections through the review's checks, record sections from files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from tests.lit_fakes import LitGenerator, LitJudge, make_lit_deps
from tests.test_paper_evidence import Fetch, make_review, parse
from vera.literature import paper, paper_stage
from vera.schemas import PaperDocument, PaperRequest, Question, SelfGradingError, Verdict

THEMES = [
    {"heading": "Design rationale", "focus": "design rationale"},
    {"heading": "Requirements traceability", "focus": "requirements traceability"},
    {"heading": "Repair history", "focus": "repair history"},
    {"heading": "Quantum widgets", "focus": "quantum widgets zebra"},  # nothing in the evidence: dropped
]
STATS = {"queries": ["a", "b", "c"], "n_retrieved": 40, "n_kept": 6, "n_read_full": 2, "n_dropped_by_screen": 34}


class MarkedJudge(LitJudge):
    """True unless the material contains UNSUPPORTED (a claim the judge must reject)."""

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        out = super().ask(state, questions)
        return [v.model_copy(update={"answer": "UNSUPPORTED" not in state}) for v in out]


def fenced(data: object) -> str:
    return "```json\n" + json.dumps(data) + "\n```"


def setup_run(tmp_path: Path, judge=None) -> tuple:
    run = make_review(tmp_path, n_papers=8)
    scope = {"topic_id": "t-a", "question": "Which information can be recovered from agent traces?",
             "why_researchable": "papers exist", "empirical": False, "status": "confirmed", "confirmed_by": "Chris",
             "confirmed_at": "2026-10-11T09:00:00Z"}  # fmt: skip
    (run / "scope.json").write_text(json.dumps(scope), encoding="utf-8")
    (run / "literature.md").write_text("## Literature review\n\nA review [R1].\n\n## References\n\n[R1] x\n", "utf-8")
    (run / "claims_judged.jsonl").write_text("", encoding="utf-8")
    deps = make_lit_deps(tmp_path, replies={"p3.paper.write": "{}"})
    deps.run_dir = run
    if judge is not None:
        deps.judge = judge
    deps.extra |= {"fetch_pdf": Fetch(), "parse_pdf": parse, "paper_request": PaperRequest(max_usd=1.0)}
    return run, deps


def sentences_on(passages: list[dict], words: str) -> list[tuple[str, str]]:
    """(source_key, sentence) for every verbatim sentence about `words` in the paper's passages."""
    out = []
    for p in passages:
        for s in re.findall(rf"{words} finding R\d+ \d+ word\d\.", p["text"]):
            out.append((p["source_key"], s))
    return list(dict.fromkeys(out))


def section(pairs: list[tuple[str, str]], extra: list[dict] = ()) -> str:
    sents = [{"text": f"Paper {k} reports {q[:-1]}.", "claim": {"source_key": k, "passage_id": "", "quote": q}}
             for k, q in pairs]  # fmt: skip
    return fenced({"paragraphs": [[*sents, *extra]]})


def run_nodes(deps, state: dict, names: list[str]) -> dict:
    factories = {n: f for n, _, f in paper_stage.PAPER_NODES}
    for name in names:
        update = factories[name](deps)(state)
        state = state | {k: v for k, v in update.items() if k not in ("trail", "stage_results")}
        state["stage_results"] = state.get("stage_results", []) + update.get("stage_results", [])
        if state.get("stop"):
            break
    return state


def script(deps, run: Path, per_theme: int = 6, theme_extra: list[dict] = ()) -> None:
    passages = [json.loads(ln) for ln in (run / "paper" / "passages.jsonl").read_text("utf-8").splitlines() if ln]
    replies = [fenced({"title": "Agent traces: a review", "themes": THEMES}),
               section(sentences_on(passages, "agent traces trajectory")[:3])]  # fmt: skip
    for t in THEMES[:3]:
        replies.append(section(sentences_on(passages, t["focus"])[:per_theme], list(theme_extra)))
    replies.append("[]")  # every repair attempt drops what failed
    deps.generator.replies["p3.paper.write"] = replies


APPEND_ONLY = {"gates.jsonl"}  # the run's gate log: every verdict, the review's and the paper's, is appended to it


def digest(run: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()
            if p.is_file() and p.name not in APPEND_ONLY}  # fmt: skip


def test_RSH_F_12_a_paper_is_made_from_a_review_without_changing_it(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    (run / "gates.jsonl").write_text('{"review": "verdict"}\n', encoding="utf-8")
    before, gates_before = digest(run), (run / "gates.jsonl").read_text(encoding="utf-8")
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    assert not state.get("stop"), state.get("stop")
    doc = PaperDocument.model_validate(state["paper"])
    assert [c.id for c in doc.claims] == [f"C{i}" for i in range(1, len(doc.claims) + 1)]
    assert len(doc.claims) >= paper_stage.MIN_PAPER_CLAIMS
    headings = [s.heading for s in doc.sections]
    assert headings[:2] == ["Introduction", "Method"] and headings[-1] == "Threats to validity"
    assert "Quantum widgets" not in headings  # the outline's unsupported theme was dropped
    md = (run / "paper" / "paper.md").read_text(encoding="utf-8")
    assert md.startswith("# Agent traces: a review") and "## References" in md
    assert digest(run) == before  # the review's own files are untouched (the paper lives in paper/)
    gates = (run / "gates.jsonl").read_text(encoding="utf-8")
    assert gates.startswith(gates_before) and len(gates) > len(gates_before)  # the gate log only grew


def test_RSH_F_12_planted_faults_are_removed_as_in_the_review(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path, judge=MarkedJudge())
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])

    def claim(key: str, quote: str) -> dict:
        return {"source_key": key, "passage_id": "", "quote": quote}

    planted = [
        {
            "text": "Paper R1 reports an invented finding.",
            "claim": claim("R1", "a sentence that appears in no passage"),
        },
        {"text": "Paper R2 reports what R1 said.", "claim": claim("R2", "Abstract of R1 about agent traces.")},
        {"text": "Paper R4 reports something UNSUPPORTED.", "claim": claim("R4", "Abstract of R4 about agent traces.")},
        {"text": "As R5 shows, traces matter.", "claim": None},
    ]
    script(deps, run, theme_extra=planted)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    verify = json.loads((run / "paper" / "verify.json").read_text(encoding="utf-8"))
    md = (run / "paper" / "paper.md").read_text(encoding="utf-8")
    for p in planted:
        assert p["text"].rstrip(".") not in md
    assert verify["stats"]["stray_attributions_removed"] == 3  # one per findings section
    assert verify["stats"]["removed"] == 9  # three planted claims in each of three sections
    assert not state.get("stop")


def test_RSH_F_12_record_sections_hold_only_numbers_from_the_run_files(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    doc = PaperDocument.model_validate(state["paper"])
    reading = json.loads((run / "paper" / "reading.json").read_text(encoding="utf-8"))
    allowed = {len(STATS["queries"]), STATS["n_retrieved"], STATS["n_kept"], STATS["n_dropped_by_screen"],
               reading["n_full_text"], reading["n_abstract_only"], reading["n_passages"],
               reading["n_full_text"] + reading["n_abstract_only"], len(doc.claims), len(doc.sources)}  # fmt: skip
    for s in doc.sections:
        if s.kind == "record":
            numbers = {int(n) for n in re.findall(r"(?<![\w.])\d+(?![\w.])", s.text)}
            assert numbers <= allowed, (s.heading, numbers - allowed)
            assert "Paper R" not in s.text  # no model sentence in a record section


def test_RSH_F_12_too_little_evidence_stops_with_the_reason(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run, per_theme=1)
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    assert state["stop"]["stage"] == "paper" and "need 15" in state["stop"]["reason"]
    assert not (run / "paper" / "paper.md").exists()


def test_RSH_F_12_the_writer_never_judges_its_own_text(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path, judge=LitJudge(judge_id="p3.paper.write"))
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run)
    with pytest.raises(SelfGradingError):
        run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])


def test_RSH_F_12_an_outline_with_too_few_supported_themes_stops(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    deps.generator.replies["p3.paper.write"] = [fenced({"title": "T", "themes": THEMES[2:]})]
    state = run_nodes(deps, state, ["paper_outline"])
    assert "need 3" in state["stop"]["reason"]
    assert isinstance(LitGenerator, type) and paper.MIN_THEMES == 3


def test_RSH_F_12_a_repair_shows_the_sections_own_passages_not_the_whole_paper(tmp_path: Path) -> None:
    """The first live paper spent most of its money on repair prompts that held every passage of the paper (Increment 6
    live run 1): a repair is shown the passages its section was drafted from, and is still checked against all."""
    run, deps = setup_run(tmp_path, judge=MarkedJudge())
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    quote = "Abstract of R4 about agent traces."
    claim = {"source_key": "R4", "passage_id": "", "quote": quote}
    bad = {"text": "Paper R4 reports something UNSUPPORTED.", "claim": claim}
    script(deps, run, theme_extra=[bad])
    prompts: list[str] = []
    generate = deps.generator.generate

    def spy(system: str, prompt: str, *, component: str) -> str:
        prompts.append(prompt)
        return generate(system, prompt, component=component)

    deps.generator.generate = spy
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    passages = [json.loads(ln) for ln in (run / "paper" / "passages.jsonl").read_text("utf-8").splitlines() if ln]
    repairs = [p for p in prompts if "failed their checks" in p]
    assert len(repairs) == 3  # one per findings section with a failure
    for p in repairs:
        shown = sum(1 for x in passages if f"<{x['id']}>" in p)
        assert 0 < shown <= paper.THEME_PASSAGES < len(passages)
