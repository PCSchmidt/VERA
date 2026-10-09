"""RSH-F-09, AUD-F-10: the literature section with checked claims, repaired once. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lit_fakes import LitJudge, fenced, make_lit_deps
from vera.literature import scoping, synthesis, synthesis_stage
from vera.schemas import LiteratureSection, StageResult

RECORDS = {
    "R1": {
        "key": "R1",
        "title": "TreeHFD",
        "authors": ["C. Benard"],
        "year": "2025",
        "id": "arXiv:2510.24815",
        "url": "https://arxiv.org/abs/2510.24815",
        "source": "arxiv",
    },
    "R2": {
        "key": "R2",
        "title": "Purifying interactions",
        "authors": ["B. Lengerich"],
        "year": "2019",
        "id": "arXiv:1911.04974",
        "url": "https://arxiv.org/abs/1911.04974",
        "source": "arxiv",
    },
    "R3": {
        "key": "R3",
        "title": "Unused paper",
        "authors": [],
        "year": "2020",
        "id": "arXiv:2001.00003",
        "url": "https://arxiv.org/abs/2001.00003",
        "source": "arxiv",
    },
}
Q1 = "the decomposition becomes unstable across bootstrap refits when correlation exceeds 0.9"
Q2 = "main effects remain close to the ground truth in the synthetic experiments"
Q3 = "purification moves interaction mass into the main effects without changing predictions"
PASSAGES = [
    {
        "source_key": "R1",
        "id": "R1-P1",
        "kind": "fulltext",
        "locator": "sec. Results, para 4",
        "text": f"In our experiments {Q1}, while the {Q2}.",
    },
    {
        "source_key": "R2",
        "id": "R2-P1",
        "kind": "fulltext",
        "locator": "sec. Method, para 2",
        "text": f"We show that {Q3}, which makes the additive model identifiable.",
    },
    {
        "source_key": "R3",
        "id": "R3-A",
        "kind": "abstract",
        "locator": "abstract",
        "text": "A paper about something quite different, with its own particular wording throughout.",
    },
]


def claim(source: str, passage: str, quote: str) -> dict:
    return {"source_key": source, "passage_id": passage, "quote": quote}


GOOD1 = {"text": "TreeHFD interactions become unstable under strong correlation.", "claim": claim("R1", "R1-P1", Q1)}
GOOD2 = {"text": "TreeHFD's main effects stay accurate.", "claim": claim("R1", "R1-P1", Q2)}
GOOD3 = {"text": "Purification keeps predictions fixed.", "claim": claim("R2", "R2-P1", Q3)}
FAKE = {"text": "Rankings are always stable.", "claim": claim("R1", "R1-P1", "rankings are always perfectly stable")}
WRONG = {"text": "Purification is unstable.", "claim": claim("R1", "R1-P1", Q3)}  # R2's quote under R1's key
GHOST = {"text": "A ninth paper agrees.", "claim": claim("R9", "R9-P1", Q1)}
LOOSE = {"text": "This agrees with Lundberg et al. on TreeSHAP.", "claim": None}
BRIDGE = {"text": "What remains unestablished is behaviour on real data.", "claim": None}


def confirm(run_dir: Path, topic_id: str) -> None:
    scoped = scoping.ScopedQuestion(
        topic_id=topic_id,
        question="q?",
        why_researchable="w",
        empirical=False,
        status="confirmed",
        confirmed_by="Chris",
        confirmed_at="2026-10-03T10:00:00Z",
    )
    scoping.write_scope(run_dir, scoped)


def deps_with_evidence(tmp_path: Path, draft: list, repair: list | None = None, *, judge=None, extra_claims=()):
    reply = json.dumps({"paragraphs": draft})
    replies = {"p3.synthesize": [reply] + ([json.dumps(repair)] if repair is not None else [])}
    deps = make_lit_deps(tmp_path, replies=replies)
    if judge:
        deps.judge = judge(deps)
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    (deps.run_dir / "retrieved.jsonl").write_text("".join(json.dumps(r) + "\n" for r in RECORDS.values()), "utf-8")
    (deps.run_dir / "passages.jsonl").write_text("".join(json.dumps(p) + "\n" for p in PASSAGES), "utf-8")
    confirm(deps.run_dir, "t-a")
    return deps


def run_nodes(deps) -> dict:
    state = synthesis_stage.synthesize_node(deps)({})
    return state | synthesis_stage.verify_node(deps)(state)


# ── the deterministic checks ────────────────────────────────────────────────────────────────────────


def test_RSH_F_09_a_claim_is_checked_against_its_source_and_its_quote() -> None:
    check = lambda c: synthesis.check_claim(c, RECORDS, PASSAGES)  # noqa: E731
    assert check(GOOD1["claim"]) == ("pass", None)
    assert check(GHOST["claim"]) == ("fail", "unresolved_source")  # a citation that is not in the retrieval log
    assert check(WRONG["claim"]) == ("fail", "wrong_source")  # a real quote under the wrong source key
    assert check(FAKE["claim"]) == ("fail", "fabricated_quote")  # a quote that is nowhere in the evidence
    assert check(claim("R1", "R1-P1", "unstable"))[0] == "fail"  # too short to prove anything


def test_RSH_F_09_citation_markers_come_from_claims_not_from_model_text() -> None:
    text, claims = synthesis.assemble([[GOOD1, BRIDGE], [GOOD3]])
    assert text == (
        "TreeHFD interactions become unstable under strong correlation [R1]. What remains unestablished "
        "is behaviour on real data.\n\nPurification keeps predictions fixed [R2]."
    )
    assert [c["source_key"] for c in claims] == ["R1", "R2"]
    refs = synthesis.references_block(claims, RECORDS)
    assert "[R1]" in refs and "[R2]" in refs and "[R3]" not in refs  # only cited sources are listed
    assert "arXiv:2510.24815" in refs  # built from the retrieval log


def test_the_model_reply_is_parsed_leniently() -> None:
    assert synthesis.parse_sentences("nonsense") == []
    parsed = synthesis.parse_sentences({"paragraphs": [[GOOD1, {"text": "", "claim": None}, "junk", BRIDGE], "x", []]})
    assert [s["text"] for s in parsed[0]] == [GOOD1["text"], BRIDGE["text"]] and len(parsed) == 1
    half = synthesis.parse_sentences({"paragraphs": [[{"text": "t", "claim": {"source_key": "R1"}}]]})
    assert half[0][0]["claim"] is None  # a claim with no quote is no claim


# ── the stage ───────────────────────────────────────────────────────────────────────────────────────


def test_RSH_F_09_the_section_keeps_only_claims_that_passed_every_check(tmp_path: Path) -> None:
    draft = [[GOOD1, GOOD2, BRIDGE], [GOOD3, FAKE, WRONG, GHOST, LOOSE]]
    repair = [{"text": None, "claim": None}, {"text": None, "claim": None}, {"text": None, "claim": None}]
    deps = deps_with_evidence(tmp_path, draft, repair)
    state = run_nodes(deps)
    section = LiteratureSection.model_validate(state["section"])
    kept = {c.claim for c in section.claims}
    assert kept == {GOOD1["text"], GOOD2["text"], GOOD3["text"]}
    text = (deps.run_dir / "literature.md").read_text(encoding="utf-8")
    assert "always stable" not in text and "ninth paper" not in text and "Lundberg" not in text  # nothing unchecked
    assert "[R9]" not in text and "[R3]" not in text and "[R1]" in text and "[R2]" in text
    stats = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))
    assert stats["stats"] == {"drafted": 6, "failed_first": 3, "repaired": 0, "removed": 3,
                              "stray_attributions_removed": 1}  # fmt: skip
    assert stats["failure_reasons"] == {"fabricated_quote": 1, "wrong_source": 1, "unresolved_source": 1}
    assert all(c.quote_check == "pass" and c.locator for c in section.claims)
    # the judge only saw claims that passed the deterministic checks (three), and with fewer than five surviving
    # claims the stage stopped before the section-level question
    assert deps.judge.asked == ["lit.claim_supported", "lit.quote_covers_claim"] * 3
    assert "only 3 claims" in state["stop"]["reason"]


def test_RSH_F_09_a_failed_claim_is_sent_back_once_and_kept_if_the_repair_passes(tmp_path: Path) -> None:
    fixed = {"text": "TreeHFD interactions are unstable at high correlation.", "claim": claim("R1", "R1-P1", Q1)}
    draft = [[GOOD2, GOOD3, FAKE, GOOD1, BRIDGE]]
    deps = deps_with_evidence(tmp_path, draft, [fixed])
    state = run_nodes(deps)
    texts = {c["claim"] for c in state["section"]["claims"]}
    assert fixed["text"] in texts and FAKE["text"] not in texts
    stats = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))["stats"]
    assert stats["repaired"] == 1 and stats["removed"] == 0
    assert deps.generator.calls == ["p3.synthesize", "p3.synthesize"]  # the draft, and exactly one repair call


def test_RSH_F_09_a_repair_that_still_fails_is_removed_and_a_judge_no_is_removed(tmp_path: Path) -> None:
    still_fake = {"text": "Still wrong.", "claim": claim("R1", "R1-P1", "a quote nobody ever wrote anywhere at all")}
    draft = [[GOOD2, GOOD3, FAKE, GOOD1, BRIDGE]]
    deps = deps_with_evidence(tmp_path, draft, [still_fake])
    state = run_nodes(deps)
    assert "Still wrong." not in {c["claim"] for c in state["section"]["claims"]}

    class Doubtful(LitJudge):
        def ask(self, state, questions):
            out = super().ask(state, questions)
            if questions[0].id == "lit.claim_supported" and "Purification keeps" in state:
                return [v.model_copy(update={"answer": False}) for v in out]
            return out

    unsupported = [[GOOD1, GOOD2, GOOD3, BRIDGE]]
    deps2 = deps_with_evidence(tmp_path / "b", unsupported, [{"text": None, "claim": None}],
                               judge=lambda d: Doubtful(d.ledger, d.budget))  # fmt: skip
    state2 = run_nodes(deps2)
    claims2 = {c["claim"] for c in state2["section"]["claims"]}
    assert GOOD3["text"] not in claims2 and GOOD1["text"] in claims2  # the judge said the passage does not support it
    reasons = json.loads((deps2.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))
    assert reasons["failure_reasons"] == {"unsupported": 1}


def test_RSH_F_09_too_few_surviving_claims_stop_the_stage(tmp_path: Path) -> None:
    deps = deps_with_evidence(tmp_path, [[GOOD1, GOOD2, BRIDGE]], None)
    state = run_nodes(deps)
    assert state["stop"]["stage"] == "synthesize" and "only 2 claims survived" in state["stop"]["reason"]
    sr = StageResult.model_validate(state["stage_results"][0])
    assert sr.decision == "reject" and sr.reason and sr.producer_id == "p3.synthesize"


def test_RSH_F_09_a_section_that_does_not_answer_the_question_is_rejected(tmp_path: Path) -> None:
    draft = [[GOOD1, GOOD2, GOOD3, BRIDGE], [GOOD1, GOOD2]]
    draft[1] = [{**GOOD1, "text": "Again unstable."}, {**GOOD2, "text": "Again accurate."}]
    no = {"lit.section_answers": False}
    deps = deps_with_evidence(tmp_path, draft, None, judge=lambda d: LitJudge(d.ledger, d.budget, answers=no))
    state = run_nodes(deps)
    assert "does not find" in state["stop"]["reason"] or "did not find" in state["stop"]["reason"]
    sr = StageResult.model_validate(state["stage_results"][0])
    assert sr.decision == "reject" and sr.gates[-1].question_id == "lit.section_answers"


def test_RSH_F_09_nothing_passing_the_deterministic_checks_stops_without_asking_the_judge(tmp_path: Path) -> None:
    deps = deps_with_evidence(tmp_path, [[FAKE, GHOST, WRONG]], [{"text": None, "claim": None}] * 3)
    state = run_nodes(deps)
    assert "no claim passed" in state["stop"]["reason"] and deps.judge.asked == []


def test_RSH_F_09_the_judge_is_not_paid_twice_for_the_same_claim(tmp_path: Path) -> None:
    deps = deps_with_evidence(tmp_path, [[GOOD1, GOOD2, GOOD3, BRIDGE], [GOOD1, GOOD2, GOOD3]], None)
    state = synthesis_stage.synthesize_node(deps)({})
    synthesis_stage.verify_node(deps)(state)
    asked = deps.judge.asked.count("lit.claim_supported")
    synthesis_stage.verify_node(deps)(state)  # the node run again: every claim verdict is cached
    assert deps.judge.asked.count("lit.claim_supported") == asked


def test_RSH_F_09_the_draft_needs_a_usable_reply(tmp_path: Path) -> None:
    deps = make_lit_deps(tmp_path, replies={"p3.synthesize": fenced({"paragraphs": []})})
    deps.run_dir.mkdir(parents=True, exist_ok=True)
    (deps.run_dir / "retrieved.jsonl").write_text(json.dumps(RECORDS["R1"]) + "\n", encoding="utf-8")
    (deps.run_dir / "passages.jsonl").write_text(json.dumps(PASSAGES[0]) + "\n", encoding="utf-8")
    confirm(deps.run_dir, "t")
    assert "no usable literature section" in synthesis_stage.synthesize_node(deps)({})["stop"]["reason"]
    unconfirmed = make_lit_deps(tmp_path / "u")
    with pytest.raises(scoping.ScopeNotConfirmedError):
        synthesis_stage.synthesize_node(unconfirmed)({})


def test_RSH_F_09_a_sentence_that_names_a_source_in_running_text_without_a_claim_is_removed(tmp_path: Path) -> None:
    """Found in the first walkthrough: 'The two studies thus differ ... although R4 examined three agents and R12 a much
    larger set' had no quote behind it, cited a source missing from the references, and the audit passed it."""
    named = {
        "text": "The two studies thus differ on length, although R1 examined three agents and R2 a larger set.",
        "claim": None,
    }
    deps = deps_with_evidence(tmp_path, [[GOOD1, named, GOOD2]], [])
    run_nodes(deps)
    text = (deps.run_dir / "literature.md").read_text(encoding="utf-8")
    assert "The two studies thus differ" not in text and "become unstable under strong correlation [R1]" in text
    stats = json.loads((deps.run_dir / "artifacts" / "literature.json").read_text(encoding="utf-8"))["stats"]
    assert stats["stray_attributions_removed"] == 1
    from vera.literature.anchoring import names_a_source_without_a_claim as names  # noqa: PLC0415

    assert (
        names("R4 examined three agents") == "R4"
        and names("As reported [R4].") is None
        and names("The FR12 code") is None
    )
