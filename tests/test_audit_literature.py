"""AUD-F-03 (on the loop's own text) and AUD-F-10: the audit of a literature section. Offline, with a scripted judge."""

from __future__ import annotations

import pytest

from vera.audit import run_literature_audit
from vera.schemas import Question, Verdict

RECORDS = [
    {"key": "R1", "title": "TreeHFD", "authors": ["Clement Benard"], "year": "2025", "id": "arXiv:2510.24815",
     "url": "https://arxiv.org/abs/2510.24815"},
    {"key": "R2", "title": "Purifying interactions", "authors": ["B. Lengerich"], "year": "2019",
     "id": "arXiv:1911.04974", "url": "https://arxiv.org/abs/1911.04974"},
    {"key": "R3", "title": "The influence of correlated features on attribution", "year": "2025",
     "authors": ["Evan Krell", "Scott A. King", "P. Tissot", "I. Ebert-Uphoff"], "id": "doi:10.1/x",
     "url": "https://doi.org/10.1/x"},
]
Q1 = "the decomposition becomes unstable across bootstrap refits when correlation exceeds 0.9"
Q2 = "purification moves interaction mass into the main effects without changing predictions"
Q3 = "synthetic data of increasing correlation shows attribution errors growing with the correlation"
PASSAGES = [
    {"source_key": "R1", "id": "R1-P1", "kind": "fulltext", "locator": "sec. Results, para 4",
     "text": f"In our experiments {Q1}, while main effects stay accurate."},
    {"source_key": "R2", "id": "R2-P1", "kind": "fulltext", "locator": "sec. Method, para 2",
     "text": f"We show that {Q2}, which makes the additive model identifiable."},
    {"source_key": "R3", "id": "R3-P1", "kind": "fulltext", "locator": "sec. Results, para 1",
     "text": f"With {Q3}, as the authors report for the neural network."},
]
S1, S2, S3 = ("TreeHFD interactions become unstable under strong correlation",
              "Purification keeps predictions fixed", "Attribution errors grow with correlation")
CLAIMS = [{"claim": S1 + ".", "source_key": "R1", "quote": Q1, "locator": "sec. Results, para 4"},
          {"claim": S2 + ".", "source_key": "R2", "quote": Q2, "locator": "sec. Method, para 2"},
          {"claim": S3 + ".", "source_key": "R3", "quote": Q3, "locator": "sec. Results, para 1"}]
REFS = ("[R1] Clement Benard. TreeHFD. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815\n"
        "[R2] B. Lengerich. Purifying interactions. 2019. arXiv:1911.04974. https://arxiv.org/abs/1911.04974\n"
        "[R3] Evan Krell, Scott A. King, P. Tissot et al.. The influence of correlated features on attribution. 2025. "
        "doi:10.1/x. https://doi.org/10.1/x")


def section(body: str = f"{S1} [R1]. {S2} [R2].\n\n{S3} [R3].", refs: str = REFS) -> str:
    return f"## Literature review\n\n{body}\n\n## References\n\n{refs}\n"


class Judge:
    def __init__(self, answer: bool = True, confident: bool = True) -> None:
        self.answer, self.confident, self.asked = answer, confident, []

    def __call__(self, q: Question, material: str) -> tuple[Verdict, bool]:
        self.asked.append(q.id)
        v = Verdict(question_id=q.id, answer=self.answer, confidence=0.9 if self.confident else 0.4,
                    confidence_source="self_report", backend="fake", escalated=False, cost_usd=0.0001, latency_ms=1,
                    trace_id="t", judge_id="p2.judge", producer_id="p3.synthesize")  # fmt: skip
        return v, self.confident


def audit(text: str, *, claims=None, passages=None, records=None, judge: Judge | None = None):
    return run_literature_audit(text, claims if claims is not None else CLAIMS, passages or PASSAGES,
                                records or RECORDS, ask=judge or Judge(), paper_id="lit-1",
                                paper_source="literature.md")  # fmt: skip


def failures(run) -> list[str]:
    return [f.summary for f in run.report.findings if f.severity == "fail"]


def test_AUD_F_10_a_section_built_from_checked_claims_is_green_and_every_claim_went_to_the_judge() -> None:
    judge = Judge()
    run = audit(section(), judge=judge)
    assert run.report.overall == "green" and run.report.findings == []
    assert judge.asked == ["lit.claim_supported"] * 3 and len(run.claims) >= 3  # citations and cited sentences
    assert run.report.checks_run == ["citation", "claim_support"]


def test_AUD_F_03_a_reference_with_an_initial_in_an_author_name_is_not_a_false_fail() -> None:
    assert audit(section()).report.findings == []  # R3's "Scott A. King" broke the first entry parser


def test_AUD_F_03_a_citation_that_is_not_a_retrieved_record_is_a_fail() -> None:
    run = audit(section(f"{S1} [R1]. {S2} [R9].\n\n{S3} [R3]."))
    assert any("[R9]" in f for f in failures(run)) and run.report.overall == "red"


def test_AUD_F_03_an_altered_reference_entry_is_a_fail() -> None:
    run = audit(section(refs=REFS.replace("Purifying interactions", "Purging interactions")))
    assert any("R2 differs from the record" in f for f in failures(run))


def test_AUD_F_10_a_cited_sentence_with_no_claim_behind_it_is_a_fail_with_evidence() -> None:
    run = audit(section(f"{S1} [R1]. A brand new sentence that no claim stands behind at all [R2].\n\n{S3} [R3]."))
    (f,) = [f for f in run.report.findings if "no claim behind it" in f.summary]
    assert f.severity == "fail" and f.evidence[0].reference == "claims.jsonl" and f.evidence[0].matched is False


def test_AUD_F_10_a_sentence_moved_to_another_source_is_a_fail() -> None:
    run = audit(section(f"{S1} [R2]. {S2} [R2].\n\n{S3} [R3]."))
    assert any("linked to [R1]" in f for f in failures(run))
    assert any("linked to [R1]" in f for f in failures(audit(section(f"{S1} [R1] [R2]. {S2} [R2].\n\n{S3} [R3]."))))


@pytest.mark.parametrize(
    ("quote", "why"),
    [
        ("rankings are always perfectly stable across every single refit we ran", "fabricated_quote"),
        (Q2, "wrong_source"),  # a real quote, but R2's, under R1
        (Q1.replace("exceeds", "may exceed"), "fabricated_quote"),  # a changed qualifier
    ],
)
def test_AUD_F_10_a_quote_that_is_not_in_the_cited_source_is_a_fail(quote: str, why: str) -> None:
    bad = [{**CLAIMS[0], "quote": quote}, *CLAIMS[1:]]
    run = audit(section(), claims=bad)
    assert any(f"({why})" in f for f in failures(run))
    assert [f.evidence[0].reference for f in run.report.findings if f.check == "claim_support"] == ["passages.jsonl#R1"]


def test_AUD_F_10_a_claim_the_judge_says_the_passage_does_not_support_is_a_fail_unsure_is_a_warn() -> None:
    no = audit(section(), judge=Judge(answer=False))
    assert len(failures(no)) == 3 and all(f.verdicts for f in no.report.findings)
    unsure = audit(section(), judge=Judge(confident=False))
    assert unsure.report.overall == "amber" and {f.severity for f in unsure.report.findings} == {"warn"}


def test_AUD_F_10_a_claim_text_swapped_for_another_claims_is_for_the_judge_to_catch() -> None:
    # the sentence and its claim agree, the quote is real, but the claim is not what the passage says
    swapped = [{**CLAIMS[0], "claim": "Purification keeps predictions fixed and doubles accuracy."}, *CLAIMS[1:]]
    body = f"Purification keeps predictions fixed and doubles accuracy [R1]. {S2} [R2].\n\n{S3} [R3]."
    run = audit(section(body), claims=swapped, judge=Judge(answer=False))
    assert any("does not support the claim" in f for f in failures(run))


def test_the_literature_audit_skips_what_it_does_not_check_and_says_so() -> None:
    run = audit(section())
    assert "novelty" in run.report.checks_skipped and "method_code" in run.report.checks_skipped
