"""Claim anchoring and the retrieval note (Increment 4): one assertion per sentence, covered by its quote."""

from __future__ import annotations

import json
from pathlib import Path

from tests.lit_fakes import LitJudge
from tests.test_synthesis import GOOD1, GOOD2, GOOD3, Q1, claim, deps_with_evidence, run_nodes
from vera.literature import anchoring
from vera.schemas import LiteratureSection, RetrievalStats


def test_an_editorial_connective_the_quote_lacks_is_a_marker_problem() -> None:
    assert anchoring.marker_problem("TreeHFD is stable, unlike TreeSHAP", "the decomposition is stable") == "unlike"
    assert anchoring.marker_problem("TreeHFD is stable", "the decomposition is stable") is None
    # a connective that is in the quote itself is the source's own wording, not the review's
    assert anchoring.marker_problem("It works, whereas the baseline fails", "works, whereas the baseline fails") is None


def test_the_quote_question_shows_the_judge_the_quote_and_nothing_else() -> None:
    q, material = anchoring.quote_covers_claim("A claim.", "the quote", "A Paper Title")
    assert q.id == "lit.quote_covers_claim" and 'Source: "A Paper Title"' in material
    assert "Quote from that source: the quote" in material and "Passage" not in material


def test_a_claim_the_quote_does_not_cover_goes_to_repair_and_is_removed_if_it_cannot_be_fixed(tmp_path: Path) -> None:
    extra = {
        "text": "Purification is exact, unlike sampling.",
        "claim": claim("R2", "R2-P1", Q1),
    }  # marker, wrong source
    draft = [[GOOD1, GOOD2, GOOD3, extra]]
    deps = deps_with_evidence(tmp_path, draft, [{"text": None, "claim": None}])
    state = run_nodes(deps)
    kept = {c["claim"] for c in LiteratureSection.model_validate(state["section"]).model_dump()["claims"]}
    assert extra["text"] not in kept
    reasons = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))[
        "failure_reasons"
    ]
    assert any(r.startswith("wrong_source") or r.startswith("unanchored") for r in reasons)


def test_a_judge_that_says_the_quote_does_not_cover_the_claim_fails_it(tmp_path: Path) -> None:
    deps = deps_with_evidence(tmp_path, [[GOOD1, GOOD2, GOOD3]], [{"text": None, "claim": None}] * 3,
                              judge=lambda d: LitJudge(d.ledger, d.budget, answers={"lit.quote_covers_claim": False}),
    )  # fmt: skip
    state = run_nodes(deps)
    reasons = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))[
        "failure_reasons"
    ]
    assert reasons == {"unanchored: the quote alone does not state the claim": 3}
    assert "only 0 claims" in state["stop"]["reason"]


def test_the_review_carries_its_retrieval_statistics_before_its_references(tmp_path: Path) -> None:
    deps = deps_with_evidence(tmp_path, [[GOOD1, GOOD2, GOOD3]])
    state = {"queries": ["q one", "q two"], "records": ["R1", "R2", "R3"], "kept": ["R1", "R2"],
             "read_report": [{"key": "R1", "mode": "fulltext"}, {"key": "R2", "mode": "abstract"}]}  # fmt: skip
    from tests.test_synthesis import synthesis_stage  # noqa: PLC0415

    state |= synthesis_stage.synthesize_node(deps)({})
    state |= synthesis_stage.verify_node(deps)(state)
    md = (deps.run_dir / "literature.md").read_text(encoding="utf-8")
    assert anchoring.has_note(md) and md.index("## Retrieval and its limits") < md.index("## References")
    assert "2 search queries" in md and "retrieved 3 candidate papers" in md and "1 were read in full text" in md
    section = LiteratureSection.model_validate(state["section"])
    assert section.retrieval_stats == RetrievalStats(queries=["q one", "q two"], n_retrieved=3, n_kept=2, n_read_full=1,
                                                     n_dropped_by_screen=1)  # fmt: skip


def test_the_note_is_inserted_once_and_works_without_a_reference_list() -> None:
    note = anchoring.retrieval_note(RetrievalStats(queries=["q"], n_retrieved=5, n_kept=2, n_read_full=0,
                                                   n_dropped_by_screen=3))  # fmt: skip
    once = anchoring.insert_note("## Review\n\ntext\n\n## References\n\n[R1] x\n", note)
    assert anchoring.insert_note(once, note) == once and once.index(note) < once.index("## References")
    assert (
        anchoring.insert_note("## Review\n\ntext\n", note)
        .rstrip()
        .endswith("topic given without a list of its key papers.")
    )


def test_dangling_reference_flags_sentences_that_lean_on_an_earlier_one():
    assert anchoring.dangling_reference("It also reports that this advantage grows with tuning time.")
    assert anchoring.dangling_reference("They report that TreeSHAP is unstable.")
    assert anchoring.dangling_reference("The authors find that this gap widens.")
    assert anchoring.dangling_reference("Grinsztajn et al. find that trees win on medium-sized data.") is None
    assert anchoring.dangling_reference("The survey reports that its authors tested nine models.") is None
