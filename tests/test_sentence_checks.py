# ruff: noqa: E501
"""RSH-F-15: every sentence of a review or a paper's evidence sections has a status, and each kind has its check.

The cases are the defects Increment 6's green audits missed (docs/reviews/incr-6.md, "What the green audits missed"):
"The two studies therefore disagree" on one source's claims, an absence statement contradicted by the paper's own
claims, "Shao and colleagues", "However, this patch may be overfitting.", a claim naming a model its quote does not,
repeated quotes, and claim-free sentences that state facts. No network; fake generator and judge.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.lit_fakes import LitJudge, make_lit_deps
from tests.test_paper_stage import STATS, run_nodes, script, setup_run
from tests.test_synthesis import confirm
from vera.literature import sentence_checks, synthesis_stage
from vera.schemas import ClaimLink, LiteratureSection, PaperDocument, Question, StageResult, Verdict

RECORDS = {
    k: {"key": k, "title": t, "authors": ["A. Author"], "year": "2025", "id": f"arXiv:2510.0000{k[1]}",
        "url": f"https://arxiv.org/abs/2510.0000{k[1]}", "source": "arxiv"}
    for k, t in [("R1", "SWE-agent study"), ("R2", "Trajectory failures"), ("R3", "Difficulty-controlled study"),
                 ("R4", "Retrieval costs")]
}  # fmt: skip
SETUP = "SWE-agent resolves 12.5% of the issues in the benchmark."
OVERFIT = "However, this patch may be overfitting to the added tests."
LONG = "Longer trajectories were associated with failure in the analysed runs of coding agents."
LONG2 = "Failed runs used more steps than successful runs across all of the analysed repositories."
REVERSE = "When task difficulty is controlled, the association between trajectory length and failure reverses."
LEANS = "This approach halves the cost of retrieval in every setting that we tried."
PASSAGES = [
    {"source_key": "R1", "id": "R1-P1", "kind": "fulltext", "locator": "sec. 4",
     "text": f"{SETUP} {OVERFIT} The authors leave this open."},
    {"source_key": "R2", "id": "R2-P1", "kind": "fulltext", "locator": "sec. 3", "text": f"{LONG} {LONG2}"},
    {"source_key": "R3", "id": "R3-P1", "kind": "fulltext", "locator": "sec. 5", "text": REVERSE},
    {"source_key": "R4", "id": "R4-P1", "kind": "fulltext", "locator": "sec. 2", "text": LEANS},
]  # fmt: skip


def cl(text: str, key: str, quote: str, ref: str) -> dict:
    return {"text": text, "claim": {"source_key": key, "passage_id": "", "quote": quote}, "ref": ref}


def loose(text: str, ref: str, kind: str = "transition", premises: tuple = ()) -> dict:
    return {"text": text, "claim": None, "kind": kind, "ref": ref, "premises": list(premises)}


C_LONG = cl("The trajectory study links longer trajectories to failure.", "R2", LONG, "s1")
C_LONG2 = cl("The trajectory study finds failed runs used more steps.", "R2", LONG2, "s2")
C_REV = cl("The difficulty-controlled study finds the association reverses.", "R3", REVERSE, "s3")


class Picky(LitJudge):
    """True unless the material contains one of `no` (question id -> substrings it rejects)."""

    def __init__(self, ledger, budget, no: dict[str, tuple[str, ...]]) -> None:
        super().__init__(ledger, budget)
        self.no, self.seen = no, []

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]:
        out = super().ask(state, questions)
        self.seen += [(q.id, state) for q in questions]
        return [v.model_copy(update={"answer": not any(s in state for s in self.no.get(v.question_id, ()))})
                for v in out]  # fmt: skip


def deps_for(tmp_path: Path, repairs: list | None = None, no: dict | None = None):
    replies = {"p3.synthesize": [json.dumps(r) for r in (repairs or [[]])]}
    deps = make_lit_deps(tmp_path, replies=replies)
    deps.judge = Picky(deps.ledger, deps.budget, no or {})
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    (deps.run_dir / "retrieved.jsonl").write_text("".join(json.dumps(r) + "\n" for r in RECORDS.values()), "utf-8")
    (deps.run_dir / "passages.jsonl").write_text("".join(json.dumps(p) + "\n" for p in PASSAGES), "utf-8")
    confirm(deps.run_dir, "t-a")
    return deps


def verify(deps, draft: list[list[dict]]) -> synthesis_stage.Verified:
    return synthesis_stage.verify_sentences(deps, {}, "Do traces predict failure?", draft, RECORDS, PASSAGES)


def outcome(checked: synthesis_stage.Verified, ref: str) -> dict:
    return next(e for e in checked.log if e["ref"] == ref)


# ── rule 1: agreement needs two sources ─────────────────────────────────────────────────────────────


def test_RSH_F_15_two_studies_disagree_on_one_sources_claims_is_removed(tmp_path: Path) -> None:
    one = loose("The two studies therefore disagree about trajectory length.", "s4", "synthesis", ("s1", "s2"))
    two = loose("The two studies disagree once task difficulty is controlled.", "s5", "synthesis", ("s1", "s3"))
    checked = verify(deps_for(tmp_path, [[]]), [[C_LONG, C_LONG2, C_REV, one, two]])
    assert outcome(checked, "s4")["status"] == "removed"
    assert "1 source" in outcome(checked, "s4")["reason"]
    assert outcome(checked, "s5")["status"] == "pass"  # premises from R2 and R3, and the judge says it follows
    assert sentence_checks.agreement_problem("Both studies agree.", ["C1", "C2"], {"C1": "R1", "C2": "R1"})
    assert sentence_checks.agreement_problem("Trajectories grow long.", ["C1"], {"C1": "R1"}) is None


# ── rule 2: absence belongs to the record ───────────────────────────────────────────────────────────


def test_RSH_F_15_an_absence_statement_in_the_evidence_is_removed_before_any_judge(tmp_path: Path) -> None:
    gone = loose("No passage covers recursive language models on cost.", "s4")
    deps = deps_for(tmp_path)
    checked = verify(deps, [[C_LONG, C_REV, gone]])
    assert outcome(checked, "s4")["status"] == "removed" and outcome(checked, "s4")["reason"].startswith("absence")
    assert not any("recursive language models" in m for _, m in deps.judge.seen)
    assert checked.stats["absence_removed"] == 1
    for text in ("None of the studies examines cost.", "The sources do not address maintenance.",
                 "Whether it helps is not yet established."):  # fmt: skip
        assert sentence_checks.absence_problem(text), text
    assert sentence_checks.absence_problem("Two studies report trajectory lengths.") is None


# ── rule 3: "X and colleagues" names a source ───────────────────────────────────────────────────────


def test_RSH_F_15_x_and_colleagues_names_a_source(tmp_path: Path) -> None:
    for text in ("Context language models were proposed by Shao and colleagues.", "Shao's team built CLMs.",
                 "Work by the Stanford group differs.", "Shao et al. and co-authors agree."):  # fmt: skip
        assert sentence_checks.names_a_source(text), text
    for text in ("The authors and their colleagues are not named.", "Trajectory studies differ in design."):
        assert sentence_checks.names_a_source(text) is None, text
    named = loose("This was later extended by Shao and colleagues.", "s4")
    checked = verify(deps_for(tmp_path), [[C_LONG, C_REV, named]])
    assert outcome(checked, "s4")["status"] == "removed" and "Shao and colleagues" in outcome(checked, "s4")["reason"]


# ── rule 4: a quote that leans on context is widened ────────────────────────────────────────────────


def test_RSH_F_15_a_quote_that_leans_on_context_is_widened_and_rechecked(tmp_path: Path) -> None:
    overfit = cl("The SWE-agent study warns that its patch may overfit the added tests.", "R1", OVERFIT, "s1")
    deps = deps_for(tmp_path)
    checked = verify(deps, [[overfit, C_REV]])
    kept = checked.paragraphs[0][0]["claim"]["quote"]
    assert kept == f"{SETUP} {OVERFIT}" and checked.stats["quotes_widened"] == 1
    assert any(q == "claim.within_quote" and SETUP in m for q, m in deps.judge.seen)  # judged on the wider quote


def test_RSH_F_15_a_leaning_quote_with_nothing_before_it_fails(tmp_path: Path) -> None:
    halves = cl("The retrieval study halves retrieval cost.", "R4", LEANS, "s1")
    checked = verify(deps_for(tmp_path, [[None]]), [[halves, C_REV]])
    assert outcome(checked, "s1")["status"] == "removed"
    assert checked.reasons == {"unanchored: the quote leans on context outside it": 1}
    assert sentence_checks.leans_on_context("However, this patch may be overfitting.")
    assert not sentence_checks.leans_on_context("SWE-agent resolves 12.5% of the issues.")
    assert sentence_checks.widen_quote(OVERFIT, PASSAGES[0]["text"]) == f"{SETUP} {OVERFIT}"
    assert sentence_checks.widen_quote(LEANS, LEANS) is None


# ── rule 5: one quote is one piece of evidence ──────────────────────────────────────────────────────


def test_RSH_F_15_a_repeated_quote_is_marked_and_counted_once() -> None:
    links = [ClaimLink(id=f"C{i}", claim=f"claim {i}", source_key=k, quote=q, locator="x", quote_check="pass")
             for i, (k, q) in enumerate([("R2", LONG), ("R3", REVERSE), ("R2", "  " + LONG.upper())], start=1)]  # fmt: skip
    marked = sentence_checks.mark_same_quotes(links)
    assert [c.same_quote_as for c in marked] == [None, None, "C1"]
    assert sentence_checks.distinct_quotes(marked) == 2


# ── the judge questions ─────────────────────────────────────────────────────────────────────────────


def test_RSH_F_15_a_claim_that_adds_a_model_name_is_removed(tmp_path: Path) -> None:
    gpt = cl("The trajectory study ran GPT-3.5-turbo agents whose longer runs failed.", "R2", LONG, "s1")
    deps = deps_for(tmp_path, [[None]], no={"claim.within_quote": ("GPT-3.5",)})
    checked = verify(deps, [[gpt, C_REV]])
    assert outcome(checked, "s1")["status"] == "removed" and checked.reasons == {"says more than its quote": 1}
    q, material = sentence_checks.within_quote(gpt["text"], LONG, "Trajectory failures")
    assert q.id == "claim.within_quote" and LONG in material and "Passage" not in material  # the quote only


def test_RSH_F_15_a_transition_that_states_a_fact_is_repaired_or_removed(tmp_path: Path) -> None:
    fact = loose("Most agents fail on long tasks.", "s4")
    fine = loose("We turn next to what predicts failure.", "s5")
    fixed = {"text": "The next paragraphs turn to failure.", "kind": "transition"}
    deps = deps_for(tmp_path, [[fixed]], no={"sentence.no_fact": ("Most agents",)})
    checked = verify(deps, [[C_LONG, C_REV, fact, fine]])
    assert outcome(checked, "s4")["status"] == "pass" and outcome(checked, "s4")["text"] == fixed["text"]
    assert outcome(checked, "s5")["status"] == "pass" and checked.stats["loose_repaired"] == 1
    deps2 = deps_for(tmp_path / "b", [[None]], no={"sentence.no_fact": ("Most agents",)})
    checked2 = verify(deps2, [[C_LONG, C_REV, fact]])
    assert outcome(checked2, "s4")["status"] == "removed"
    assert outcome(checked2, "s4")["reason"] == "a transition that states a fact"
    assert "Most agents" not in json.dumps(checked2.paragraphs)


def test_RSH_F_15_a_synthesis_whose_premise_was_removed_is_repaired_then_removed(tmp_path: Path) -> None:
    fake = cl("The trajectory study proves length causes failure.", "R2", "length causes every failure we saw", "s2")
    syn = loose("Taken together, trajectory length tracks failure.", "s4", "synthesis", ("s1", "s2"))
    still = {"text": "Taken together, length tracks failure.", "kind": "synthesis", "premises": ["s2"]}
    deps = deps_for(tmp_path, [[None], [still]])  # the claim repair drops the fake; the synthesis repair keeps s2
    checked = verify(deps, [[C_LONG, fake, C_REV, syn]])
    assert outcome(checked, "s2")["status"] == "removed"
    assert outcome(checked, "s4")["status"] == "removed" and "premise removed" in outcome(checked, "s4")["reason"]
    good = {"text": "Taken together, length tracks failure.", "kind": "synthesis", "premises": ["s1"]}
    checked2 = verify(deps_for(tmp_path / "b", [[None], [good]]), [[C_LONG, fake, C_REV, syn]])
    assert outcome(checked2, "s4")["status"] == "pass" and outcome(checked2, "s4")["premises"] == ["s1"]


def test_RSH_F_15_a_synthesis_judged_not_to_follow_is_removed(tmp_path: Path) -> None:
    over = loose("So trajectory length always causes failure.", "s4", "synthesis", ("s1",))
    deps = deps_for(tmp_path, [[None]], no={"paper.inference_follows": ("always causes",)})
    checked = verify(deps, [[C_LONG, C_REV, over]])
    assert outcome(checked, "s4")["status"] == "removed"
    assert outcome(checked, "s4")["reason"] == "does not follow from its premises"
    assert any(q == "paper.inference_follows" and "always causes" in m for q, m in deps.judge.seen)


# ── typed drafts, records and the review end to end ─────────────────────────────────────────────────


def test_RSH_F_15_typed_sentences_are_read_beside_the_frozen_parser() -> None:
    data = {"paragraphs": [[{"text": "A claim.", "claim": {"source_key": "R1", "quote": "q" * 30}, "ref": "s1"},
                            {"text": "", "claim": None}, "junk",
                            {"text": "So it holds.", "claim": None, "kind": "synthesis", "premises": ["s1"], "ref": "s2"},
                            {"text": "Next.", "claim": None}]]}  # fmt: skip
    para = sentence_checks.parse_typed(data)[0]
    assert [(s["kind"], s["ref"], s["premises"]) for s in para] == [
        ("claim", "s1", []), ("synthesis", "s2", ["s1"]), ("transition", "s3", [])
    ]  # fmt: skip
    old = sentence_checks.ensure_typed([[{"text": "x", "claim": None}, {"text": "y", "claim": None}]])
    assert [s["kind"] for s in old[0]] == ["transition", "transition"] and old[0][0]["ref"] != old[0][1]["ref"]


def test_RSH_F_15_the_review_records_every_sentence_with_claim_ids(tmp_path: Path) -> None:
    claims = [cl(f"The trajectory study finding {i}.", "R2", q, f"s{i}") for i, q in enumerate([LONG, LONG2], 1)]
    claims += [cl("The difficulty-controlled study finds a reversal.", "R3", REVERSE, "s3"),
               cl("The SWE-agent study resolves 12.5% of issues.", "R1", SETUP, "s4"),
               cl("The trajectory study links length to failure again.", "R2", LONG, "s5")]  # fmt: skip
    syn = loose("The two kinds of study differ on trajectory length.", "s6", "synthesis", ("s1", "s3"))
    draft = {"paragraphs": [[*claims, syn, loose("We turn to repair.", "s7"), loose("No study measures cost.", "s8")]]}
    deps = deps_for(tmp_path)
    deps.generator.replies["p3.synthesize"] = [json.dumps(draft), "[]"]
    state = synthesis_stage.synthesize_node(deps)({})
    state |= synthesis_stage.verify_node(deps)(state)
    assert not state.get("stop"), state.get("stop")
    section = LiteratureSection.model_validate(state["section"])
    assert [c.id for c in section.claims] == ["C1", "C2", "C3", "C4", "C5"]
    assert section.claims[4].same_quote_as == "C1"
    by_text = {s.text: s for s in section.sentences}
    assert by_text[syn["text"]].kind == "synthesis" and by_text[syn["text"]].premises == ["C1", "C3"]
    assert by_text["We turn to repair."].kind == "transition" and by_text["We turn to repair."].status == "pass"
    assert by_text["No study measures cost."].status == "removed"
    assert [s.id for s in section.sentences] == [f"S{i}" for i in range(1, 9)]
    rows = [json.loads(ln) for ln in (deps.run_dir / "claims.jsonl").read_text("utf-8").splitlines()]
    assert rows[0]["id"] == "C1"
    stats = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text("utf-8"))["stats"]
    assert stats["distinct_quotes"] == 4 and stats["synthesis_drafted"] == 1 and stats["absence_removed"] == 1


def test_RSH_F_15_the_producer_never_judges_its_sentences(tmp_path: Path) -> None:
    syn = loose("The two kinds of study differ on trajectory length.", "s4", "synthesis", ("s1", "s3"))
    checked = verify(deps_for(tmp_path), [[C_LONG, C_LONG2, C_REV, syn, loose("We turn to repair.", "s5")]])
    judges = {v.judge_id for e in checked.log for v in e["verdicts"]}
    assert judges == {"p2.judge"}  # every verdict on a sentence comes from the judge path, not p3.synthesize
    asked = {v.question_id for e in checked.log for v in e["verdicts"]}
    assert {"claim.within_quote", "paper.inference_follows", "sentence.no_fact"} <= asked


def test_RSH_F_15_the_paper_records_its_sentences_and_counts_distinct_quotes(tmp_path: Path) -> None:
    run, deps = setup_run(tmp_path)
    state = run_nodes(deps, {"section": {"retrieval_stats": STATS}}, ["paper_widen"])
    script(deps, run, theme_extra=[{"text": "We turn to the next theme.", "claim": None, "kind": "transition"}])
    state = run_nodes(deps, state, ["paper_outline", "paper_write", "paper_verify"])
    assert not state.get("stop"), state.get("stop")
    doc = PaperDocument.model_validate(state["paper"])
    kinds = {s.kind for s in doc.sentences}
    assert kinds == {"claim", "transition"}
    kept_claims = [c for s in doc.sentences if s.status == "pass" for c in s.claims]
    assert kept_claims == [c.id for c in doc.claims]  # every kept claim sentence carries its claim, in order
    assert doc.evidence_stats["distinct_quotes"] <= len(doc.claims)
    assert "distinct quotes" in doc.sections[1].text or doc.evidence_stats["distinct_quotes"] == len(doc.claims)
    verify_json = json.loads((run / "paper" / "verify.json").read_text("utf-8"))
    assert len(verify_json["sentences"]) == len(doc.sentences)
    sr = StageResult.model_validate(state["stage_results"][-1])
    assert all(g.judge_id != sr.producer_id for g in sr.gates)


def test_RSH_F_15_both_drafting_prompts_ask_for_typed_sentences(tmp_path: Path) -> None:
    from vera.literature import paper

    prompt = paper.section_prompt("q?", "Findings", "Say what is found.", PASSAGES, RECORDS, 300, None)
    assert sentence_checks.SENTENCE_RULE in prompt
    deps = deps_for(tmp_path)
    deps.generator.replies["p3.synthesize"] = [json.dumps({"paragraphs": [[C_LONG]]})]
    seen = []
    real = deps.generator.generate
    deps.generator.generate = lambda system, prompt, component: seen.append(prompt) or real(system, prompt, component=component)
    synthesis_stage.synthesize_node(deps)({})
    assert sentence_checks.SENTENCE_RULE in seen[0]
