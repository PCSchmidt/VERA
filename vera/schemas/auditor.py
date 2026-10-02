"""Auditor (P1) schemas: docs/03-interfaces.md, "Auditor"."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from vera.schemas.judge import Verdict
from vera.schemas.version import SCHEMA_VERSION


class Location(BaseModel):
    page: int | None = None
    section: str | None = None
    table: str | None = None
    quote: str | None = None  # short excerpt only


class Claim(BaseModel):
    id: str
    kind: Literal["numeric", "citation", "method", "novelty"]
    text: str
    value: float | None = None  # numeric claims
    location: Location


class Evidence(BaseModel):
    claim_id: str
    source: Literal["paper", "bibliography_api", "repo", "log", "rerun", "prior_work"]
    reference: str  # URL, DOI, file path + line, log line
    matched: bool | None  # None = could not determine
    detail: str | None = None


class Finding(BaseModel):
    check: Literal["citation", "numeric", "claim_support", "method_code", "spec_leakage", "novelty", "rerun"]
    severity: Literal["info", "warn", "fail"]
    claim_ids: list[str]
    evidence: list[Evidence]
    verdicts: list[Verdict]
    summary: str


class AuditReport(BaseModel):
    paper_id: str
    paper_source: str  # URL or path
    repo: str | None
    findings: list[Finding]
    overall: Literal["green", "amber", "red"]
    checks_run: list[str]
    checks_skipped: dict[str, str]  # check -> reason
    total_cost_usd: float
    wall_seconds: int
    schema_version: str = SCHEMA_VERSION
