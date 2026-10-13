"""Review paper schemas (Increment 6): docs/03-interfaces.md, "Review paper"."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from vera.schemas.judge import Verdict
from vera.schemas.literature import ClaimLink, RetrievalStats, SourceRecord

SectionKind = Literal["summary", "record", "evidence", "interpretation"]
SOURCE_MARKER = re.compile(r"\[R\d+\]")
MAX_EMPHASIS_CHARS = 500
MAX_USD_ALLOWED = 25.0


class PaperSection(BaseModel):
    heading: str
    kind: SectionKind
    text: str

    @field_validator("heading")
    @classmethod
    def _heading(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a section needs a heading")
        return v


class Inference(BaseModel):
    id: str
    section: str
    text: str
    premises: list[str]
    verdicts: list[Verdict] = []
    status: Literal["pass", "removed"]
    reason: str | None = None

    @model_validator(mode="after")
    def _premises(self) -> Inference:
        if self.status == "pass" and not self.premises:
            raise ValueError("a kept inference rests on at least one claim")
        return self


class PaperRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_usd: float
    length_words: Literal[3000, 5000] = 3000
    emphasis: str | None = None

    @field_validator("max_usd")
    @classmethod
    def _usd(cls, v: float) -> float:
        if not 0 < v <= MAX_USD_ALLOWED:
            raise ValueError(f"max_usd must be above 0 and at most {MAX_USD_ALLOWED:g}")
        return v

    @field_validator("emphasis")
    @classmethod
    def _emphasis(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > MAX_EMPHASIS_CHARS:
            raise ValueError(f"emphasis must be at most {MAX_EMPHASIS_CHARS} characters")
        return v.strip() or None


class PaperDocument(BaseModel):
    run_id: str
    question: str
    title: str
    sections: list[PaperSection]
    claims: list[ClaimLink]
    inferences: list[Inference]
    sources: list[SourceRecord]
    retrieval_stats: RetrievalStats | None = None
    evidence_stats: dict[str, int] = {}

    @model_validator(mode="after")
    def _checks(self) -> PaperDocument:
        kinds = {s.kind for s in self.sections}
        if "evidence" not in kinds or "record" not in kinds:
            raise ValueError("a paper needs at least one evidence section and one record section")
        ids = [c.id for c in self.claims]
        if any(not i for i in ids):
            raise ValueError("every claim in a paper needs an id")
        if len(set(ids)) != len(ids):
            raise ValueError("claim ids must be unique")
        if any(c.quote_check != "pass" for c in self.claims):
            raise ValueError("a paper keeps only claims whose quote check passed")
        unknown = sorted({c.source_key for c in self.claims} - {s.key for s in self.sources})
        if unknown:
            raise ValueError(f"claims cite sources that were not retrieved: {unknown}")
        interpretation = {s.heading for s in self.sections if s.kind == "interpretation"}
        for s in self.sections:
            if s.kind == "interpretation" and SOURCE_MARKER.search(s.text):
                raise ValueError(
                    f"interpretation section {s.heading!r} cites a source directly; it may cite claims only"
                )
        known = set(ids)
        for inf in (i for i in self.inferences if i.status == "pass"):  # a removed one is on record with its fault
            missing = sorted(set(inf.premises) - known)
            if missing:
                raise ValueError(f"inference {inf.id} rests on claims that do not exist: {missing}")
            if inf.section not in interpretation:
                raise ValueError(f"inference {inf.id} is not in an interpretation section")
        return self
