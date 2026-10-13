"""v0.13 schemas (docs/03, "Sentence status"): SentenceRecord and the rules that make reviews and papers raise."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.test_paper_schemas import claim, paper, source
from tests.test_schemas import verdict
from vera.schemas import SCHEMA_VERSION, Finding, LiteratureSection, PaperDocument, SentenceRecord

ROOT = Path(__file__).resolve().parents[1]


def sentence(**kw: object) -> SentenceRecord:
    fields = {"id": "S1", "section": "Findings", "text": "Agents release trajectories [R1].", "kind": "claim",
              "claims": ["C1"], "status": "pass"}  # fmt: skip
    return SentenceRecord(**(fields | kw))


def review(**kw: object) -> LiteratureSection:
    fields = {"run_id": "r-1", "topic_id": "t-1", "text": "Agents release trajectories [R1].", "claims": [claim()],
              "sources": [source()]}  # fmt: skip
    return LiteratureSection(**(fields | kw))


def test_RSH_F_15_schema_version_is_0_13() -> None:
    assert SCHEMA_VERSION == "0.13"


def test_RSH_F_15_sentence_records_round_trip_in_a_paper_and_a_review() -> None:
    sents = [
        sentence(),
        sentence(id="S2", kind="synthesis", claims=[], premises=["C1"], text="So traces exist.", verdicts=[verdict()]),
        sentence(id="S3", kind="transition", claims=[], text="We turn to repair."),
        sentence(id="S4", kind="synthesis", claims=[], premises=[], status="removed", reason="no premise"),
    ]
    doc = paper(sentences=sents)
    assert PaperDocument.model_validate_json(doc.model_dump_json()) == doc
    rev = review(sentences=[s.model_copy(update={"section": ""}) for s in sents])
    assert LiteratureSection.model_validate_json(rev.model_dump_json()) == rev


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "claim", "claims": []},  # a kept claim sentence carries a claim
        {"kind": "synthesis", "claims": [], "premises": []},  # a kept synthesis names a premise
        {"kind": "transition", "claims": ["C1"]},  # a transition states no fact
        {"kind": "transition", "claims": [], "premises": ["C1"]},
    ],
)
def test_RSH_F_15_a_malformed_sentence_raises(fields: dict) -> None:
    with pytest.raises(ValidationError):
        sentence(**fields)


def test_RSH_F_15_a_document_raises_on_repeated_ids_and_unknown_claims() -> None:
    with pytest.raises(ValidationError, match="unique"):
        paper(sentences=[sentence(), sentence()])
    with pytest.raises(ValidationError, match="do not exist"):
        paper(sentences=[sentence(claims=["C9"])])
    with pytest.raises(ValidationError, match="do not exist"):
        review(sentences=[sentence(section="", kind="synthesis", claims=[], premises=["C9"])])
    with pytest.raises(ValidationError, match="not evidence sections"):
        paper(sentences=[sentence(section="Discussion")])
    # a removed sentence is on record with its fault and is not held to the rules
    paper(sentences=[sentence(claims=["C9"], status="removed", reason="claim removed")])


def test_RSH_F_15_a_review_without_claim_ids_names_no_claims() -> None:
    with pytest.raises(ValidationError, match="do not exist"):
        review(claims=[claim(cid=None)], sentences=[sentence(section="")])


def test_AUD_F_12_finding_check_takes_sentence() -> None:
    f = Finding(check="sentence", severity="warn", claim_ids=[], evidence=[], verdicts=[verdict()],
                summary="a claim-free sentence states a fact")  # fmt: skip
    assert f.check == "sentence"


def test_RSH_F_15_papers_made_before_0_13_still_load() -> None:
    files = sorted((ROOT / "data" / "paper_demo").glob("*/paper/paper.json"))
    assert len(files) == 3
    for f in files:
        doc = PaperDocument.model_validate(json.loads(f.read_text(encoding="utf-8")))
        assert doc.sentences == []
