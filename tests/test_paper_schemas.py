"""v0.12 schemas (docs/03, "Review paper"): the paper's types and the rules that make them raise."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.test_schemas import verdict
from vera.schemas import (
    SCHEMA_VERSION,
    ClaimLink,
    Finding,
    Inference,
    PaperDocument,
    PaperRequest,
    PaperSection,
    SourceRecord,
)


def source(key: str = "R1") -> SourceRecord:
    return SourceRecord(
        key=key, id="arXiv:2405.15793", title="SWE-agent", source="arxiv", url="https://arxiv.org/abs/x"
    )


def claim(cid: str | None = "C1", key: str = "R1", **kw: object) -> ClaimLink:
    fields = {"id": cid, "claim": "Agents release trajectories.", "source_key": key, "quote": "we release trajectories",
              "locator": "abstract", "quote_check": "pass"}  # fmt: skip
    return ClaimLink(**(fields | kw))


def inference(**kw: object) -> Inference:
    fields = {"id": "I1", "section": "Discussion", "text": "Trajectories are available to study.", "premises": ["C1"],
              "verdicts": [verdict()], "status": "pass"}  # fmt: skip
    return Inference(**(fields | kw))


def paper(**kw: object) -> PaperDocument:
    fields = {
        "run_id": "r-1", "question": "What can agent traces tell us?", "title": "Agent traces: a review",
        "sections": [
            PaperSection(heading="Abstract", kind="summary", text="We review."),
            PaperSection(heading="Method", kind="record", text="12 queries."),
            PaperSection(heading="Findings", kind="evidence", text="Agents release trajectories [R1]."),
            PaperSection(heading="Discussion", kind="interpretation", text="Trajectories are available to study (C1)."),
        ],
        "claims": [claim()], "inferences": [inference()], "sources": [source()],
        "evidence_stats": {"n_full_text": 6, "n_abstract_only": 42},
    }  # fmt: skip
    return PaperDocument(**(fields | kw))


def test_RSH_F_12_paper_document_round_trips() -> None:
    doc = paper()
    assert PaperDocument.model_validate_json(doc.model_dump_json()) == doc
    assert SCHEMA_VERSION in ("0.12", "0.13")  # 0.13 adds sentence status


def test_RSH_F_12_claim_link_id_is_optional_so_stored_claims_still_load() -> None:
    old = {"claim": "x", "source_key": "R1", "quote": "a verbatim span", "locator": "abstract"}
    assert ClaimLink.model_validate(old).id is None


def test_RSH_F_12_paper_needs_evidence_and_record_sections() -> None:
    only_evidence = [PaperSection(heading="Findings", kind="evidence", text="x [R1].")]
    with pytest.raises(ValidationError, match="record section"):
        paper(sections=only_evidence, inferences=[])


@pytest.mark.parametrize(
    "claims, match",
    [
        ([claim(cid=None)], "needs an id"),
        ([claim(), claim()], "unique"),
        ([claim(quote_check="unchecked")], "quote check passed"),
        ([claim(key="R9")], "not retrieved"),
    ],
)
def test_RSH_F_12_bad_claims_raise(claims: list[ClaimLink], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        paper(claims=claims)


def test_RSH_F_13_interpretation_may_not_cite_sources_directly() -> None:
    sections = paper().sections[:3] + [PaperSection(heading="Discussion", kind="interpretation", text="So [R1].")]
    with pytest.raises(ValidationError, match="cites a source directly"):
        paper(sections=sections)


def test_RSH_F_13_inference_premises_must_exist_and_sit_in_interpretation() -> None:
    with pytest.raises(ValidationError, match="do not exist"):
        paper(inferences=[inference(premises=["C7"])])
    with pytest.raises(ValidationError, match="not in an interpretation section"):
        paper(inferences=[inference(section="Findings")])
    with pytest.raises(ValidationError, match="at least one claim"):
        inference(premises=[])


def test_AUD_F_11_finding_accepts_the_inference_check() -> None:
    f = Finding(check="inference", severity="fail", claim_ids=["I1"], evidence=[], verdicts=[], summary="adds a fact")
    assert f.check == "inference"


def test_APP_F_04_paper_request_limits() -> None:
    assert PaperRequest(max_usd=0.75).length_words == 3000
    assert PaperRequest(max_usd=1, emphasis="  ").emphasis is None
    for bad in ({"max_usd": 0}, {"max_usd": 26}, {"max_usd": 1, "length_words": 4000},
                {"max_usd": 1, "emphasis": "x" * 501}, {"max_usd": 1, "key": "sk-or-x"}):  # fmt: skip
        with pytest.raises(ValidationError):
            PaperRequest(**bad)
