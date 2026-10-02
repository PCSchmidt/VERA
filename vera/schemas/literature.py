"""Literature stage schemas (Increment 3): docs/03-interfaces.md, "Literature stage"."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from vera.schemas.judge import Verdict

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class Topic(BaseModel):
    id: str  # filename-safe
    text: str
    key_papers_ref: str | None = None  # data/topics/<id>.json; the recall measure for retrieval

    @field_validator("id")
    @classmethod
    def _id_ok(cls, v: str) -> str:
        if not _ID.fullmatch(v):
            raise ValueError("topic id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
        return v

    @field_validator("text")
    @classmethod
    def _text_ok(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic text must not be empty")
        return v


class ScopedQuestion(BaseModel):
    topic_id: str
    question: str
    why_researchable: str
    empirical: bool
    candidate_parent: str | None = None  # parent id (arXiv id or DOI) for an empirical question
    no_parent_reason: str | None = None
    status: Literal["proposed", "confirmed", "edited"] = "proposed"
    confirmed_by: str | None = None
    confirmed_at: str | None = None  # ISO 8601 UTC

    @model_validator(mode="after")
    def _checks(self) -> ScopedQuestion:
        if not self.question.strip() or not self.why_researchable.strip():
            raise ValueError("a scoped question needs the question and why it is researchable")
        if self.status != "proposed" and not (self.confirmed_by and self.confirmed_at):
            raise ValueError("a confirmed or edited question must record who confirmed it and when")
        if self.status == "proposed" and (self.confirmed_by or self.confirmed_at):
            raise ValueError("a proposed question has no confirmation")
        if not self.empirical and self.candidate_parent:
            raise ValueError("a non-empirical question has no parent problem")
        return self


class SourceRecord(BaseModel):
    key: str  # R1, R2, ...: what the text cites
    id: str  # arXiv:..., doi:..., or the source's own id
    title: str
    authors: list[str] = []
    year: str | None = None
    venue: str | None = None
    source: Literal["arxiv", "crossref", "openalex"]
    url: str
    abstract: str | None = None
    pdf_url: str | None = None  # open-access full text, when there is one
    query: str | None = None  # the query that retrieved it
    rank: int | None = None
    retrieved: str | None = None  # date


class ClaimLink(BaseModel):
    claim: str
    source_key: str
    quote: str = Field(min_length=1)  # a verbatim (normalised) span of the source's text
    locator: str  # where in the source: "abstract", "sec. 3", "p. 4", a passage id
    quote_check: Literal["pass", "fail", "unchecked"] = "unchecked"  # deterministic: is the quote in the text?
    verdicts: list[Verdict] = []  # lit.claim_supported, from a component other than the producer

    @field_validator("quote")
    @classmethod
    def _quote_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a claim needs a quoted passage")
        return v


class LiteratureSection(BaseModel):
    run_id: str
    topic_id: str
    text: str  # the section as written, citing [Rn]
    claims: list[ClaimLink]
    sources: list[SourceRecord]

    @model_validator(mode="after")
    def _claims_cite_sources(self) -> LiteratureSection:
        keys = {s.key for s in self.sources}
        unknown = sorted({c.source_key for c in self.claims} - keys)
        if unknown:
            raise ValueError(f"claims cite sources that were not retrieved: {unknown}")
        return self
