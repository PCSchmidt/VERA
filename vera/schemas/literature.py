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
    scope_hint: str | None = None  # the user's note on the path and what a good question looks like (never key papers)

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
    source: Literal["arxiv", "crossref", "openalex", "semanticscholar"]
    url: str
    abstract: str | None = None
    pdf_url: str | None = None  # open-access full text, when there is one
    query: str | None = None  # the query that retrieved it
    rank: int | None = None
    retrieved: str | None = None  # date


class ClaimLink(BaseModel):
    id: str | None = None  # 0.12: "C1", "C2", ... in reading order in a paper; interpretation cites these
    claim: str
    source_key: str
    quote: str = Field(min_length=1)  # a verbatim (normalised) span of the source's text
    locator: str  # where in the source: "abstract", "sec. 3", "p. 4", a passage id
    quote_check: Literal["pass", "fail", "unchecked"] = "unchecked"  # deterministic: is the quote in the text?
    verdicts: list[Verdict] = []  # lit.claim_supported, from a component other than the producer
    same_quote_as: str | None = None  # 0.13: the earlier claim whose source and quote this one reuses

    @field_validator("quote")
    @classmethod
    def _quote_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("a claim needs a quoted passage")
        return v


class RetrievalStats(BaseModel):
    """What the literature stage did, stated in the review text: a review is conditional on what retrieval found."""

    queries: list[str]
    n_retrieved: int = Field(ge=0)  # candidates before the screen
    n_kept: int = Field(ge=0)  # kept by the relevance screen
    n_read_full: int = Field(ge=0)  # read in full text; the rest at the abstract
    n_dropped_by_screen: int = Field(ge=0)


SentenceKind = Literal["claim", "synthesis", "transition"]


class SentenceRecord(BaseModel):
    """0.13 (RSH-F-15, AUD-F-12): one sentence of a review or a paper's evidence sections, with its check's outcome."""

    id: str  # "S1", "S2", ... in reading order
    section: str = ""  # heading of the section it is in ("" in a review)
    text: str
    kind: SentenceKind
    claims: list[str] = []  # claim ids the sentence carries (kind "claim")
    premises: list[str] = []  # claim ids a synthesis rests on
    verdicts: list[Verdict] = []  # from a component other than the producer
    status: Literal["pass", "removed"]
    reason: str | None = None  # for a removal: the rule or judge question that removed it

    @model_validator(mode="after")
    def _shape(self) -> SentenceRecord:
        if self.kind == "transition" and (self.claims or self.premises):
            raise ValueError(f"transition {self.id} carries claims or premises; it states no fact")
        if self.status == "pass":
            if self.kind == "claim" and not self.claims:
                raise ValueError(f"claim sentence {self.id} carries no claim")
            if self.kind == "synthesis" and not self.premises:
                raise ValueError(f"synthesis {self.id} names no premise")
        return self


def check_sentences(sentences: list[SentenceRecord], claim_ids: set[str]) -> None:
    """Document-level rules shared by reviews and papers: unique sentence ids, kept sentences name existing claims."""
    ids = [s.id for s in sentences]
    if len(set(ids)) != len(ids):
        raise ValueError("sentence ids must be unique")
    for s in (s for s in sentences if s.status == "pass"):  # a removed one is on record with its fault
        missing = sorted((set(s.claims) | set(s.premises)) - claim_ids)
        if missing:
            raise ValueError(f"sentence {s.id} names claims that do not exist: {missing}")


class LiteratureSection(BaseModel):
    run_id: str
    topic_id: str
    text: str  # the section as written, citing [Rn]
    claims: list[ClaimLink]
    sources: list[SourceRecord]
    retrieval_stats: RetrievalStats | None = None  # Increment 4: disclosed in the review text
    sentences: list[SentenceRecord] = []  # 0.13: every sentence with its status; [] for reviews made before

    @model_validator(mode="after")
    def _claims_cite_sources(self) -> LiteratureSection:
        keys = {s.key for s in self.sources}
        unknown = sorted({c.source_key for c in self.claims} - keys)
        if unknown:
            raise ValueError(f"claims cite sources that were not retrieved: {unknown}")
        check_sentences(self.sentences, {c.id for c in self.claims if c.id})
        return self


class ParentCandidate(BaseModel):
    """One candidate parent problem for an empirical question: a method paper, its repository and what it would take."""

    source_key: str  # the retrieved paper it came from (`Rn`)
    paper_id: str
    title: str
    repo_url: str
    repo_resolves: bool  # looked up live (GitHub API), never taken from model text
    licence: str | None = None  # SPDX id the host reports; None = none recorded
    pushed_at: str | None = None
    archived: bool = False
    own_code: Literal["yes", "no", "unclear"] = "unclear"  # whether the paper presents this repository as its own code
    url_context: str = ""  # the sentence of the paper that names the repository
    datasets: list[str] = Field(default_factory=list)
    compute: str = ""  # the compute the baseline needs
    compute_basis: Literal["stated", "inferred", "unknown"] = "unknown"
    cpu_minutes: float | None = None  # the model's estimate for one baseline replication on CPU; None when unknown
    harness_in_docker: str | None = None  # docker/ directory whose Dockerfile builds this repository, if any
    notes: str = ""


class ParentSelection(BaseModel):
    run_id: str
    topic_id: str
    question: str
    candidates: list[ParentCandidate]
    picked: str | None = None  # the picked candidate's repo_url
    none_fits_reason: str | None = None
    verdicts: list[Verdict] = Field(default_factory=list)  # `lit.parent_fits`, one per candidate the judge saw
    user_review: dict | None = None  # {"right": bool, "note": str, "by": str, "at": str}: the user's reading

    @model_validator(mode="after")
    def _pick_or_reason(self) -> ParentSelection:
        if (self.picked is None) == (self.none_fits_reason is None):
            raise ValueError("a selection either picks a candidate or says why none fits, not both and not neither")
        if self.picked is not None and self.picked not in {c.repo_url for c in self.candidates}:
            raise ValueError("the picked repository is not one of the candidates")
        return self
