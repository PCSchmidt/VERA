"""App contracts (docs/03 0.11): the run form's request, a run's status, and what the first-run checklist shows."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from vera.schemas.research import OutputGuidance

RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,63}")
MAX_TOPIC_CHARS = 2000
MAX_USD_ALLOWED = 25.0


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    topic: str
    guidance: OutputGuidance = OutputGuidance()
    max_usd: float
    max_wall_seconds: int
    allow_experiments: bool = False

    @field_validator("run_id")
    @classmethod
    def _run_id(cls, v: str) -> str:
        if not RUN_ID.fullmatch(v):
            raise ValueError("run_id must be 3 to 64 characters of a-z, 0-9 and '-', starting with a letter or digit")
        return v

    @field_validator("topic")
    @classmethod
    def _topic(cls, v: str) -> str:
        if not v.strip() or len(v) > MAX_TOPIC_CHARS:
            raise ValueError(f"topic must be non-blank and at most {MAX_TOPIC_CHARS} characters")
        return v.strip()

    @field_validator("max_usd")
    @classmethod
    def _usd(cls, v: float) -> float:
        if not 0 < v <= MAX_USD_ALLOWED:
            raise ValueError(f"max_usd must be above 0 and at most {MAX_USD_ALLOWED:g}")
        return v

    @field_validator("max_wall_seconds")
    @classmethod
    def _wall(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_wall_seconds must be positive")
        return v


class RunStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    state: Literal["queued", "scoping", "awaiting_confirmation", "running", "stopping", "stopped", "complete", "failed"]
    stage: str | None = None
    spent_usd: float = 0.0
    max_usd: float
    started_at: str | None = None
    updated_at: str | None = None
    last_verdict: dict | None = None
    message: str | None = None
    audit: Literal["green", "amber", "red"] | None = None


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    docker_available: bool
    grobid_available: bool
    key_source: Literal["env", "session", "none"]
    openalex_key: bool
    semantic_scholar_key: bool
