# 03 — Interfaces (core schemas)

Version 0.6 · Draft · Changes require a version bump and a changelog line.

These are the contracts between layers. Implement as Pydantic v2 models in
`vera/schemas/`. Field lists are normative; the Python below is a sketch.

## Judge layer (P2)

```python
from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field

class QuestionType(str, Enum):
    CHOICE = "choice"     # pick one of `options`
    SCORE = "score"       # integer on a rubric scale
    BOOLEAN = "boolean"   # true/false with probability

class Question(BaseModel):
    id: str                          # stable ID, e.g. "aud.cite.exists"
    type: QuestionType
    text: str                        # one atomic question
    options: list[str] | None = None # CHOICE only
    scale: tuple[int, int] | None = None  # SCORE only, e.g. (1, 5)
    rubric: str | None = None        # SCORE guidance

class Verdict(BaseModel):
    question_id: str
    answer: str | int | bool
    probabilities: dict[str, float] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_source: Literal["logprobs", "self_report", "none"] | None = None
                                     # where confidence came from: "logprobs" = the model's own probabilities
                                     # (token log-probabilities, or a decision model's native distribution);
                                     # "self_report" = probability the model states; "none" = malformed (confidence 0)
    backend: str                     # which backend produced the final answer
    escalated: bool                  # True if any cheaper backend was bypassed
    cost_usd: float
    latency_ms: int
    trace_id: str
    producer_id: str | None = None   # component that produced the judged artifact
    judge_id: str                    # component issuing this verdict (must != producer_id)

class JudgeBackend(Protocol):
    name: str
    cost_rank: int                   # lower = tried first
    def ask(self, state: str, questions: list[Question]) -> list[Verdict]: ...

class RoutingPolicy(BaseModel):
    default_threshold: float = 0.7
    per_type: dict[QuestionType, float] = {}   # per question type (JDG-F-03)
    per_question: dict[str, float] = {}        # per question id; overrides per_type
    max_escalations: int = 1
    # Precedence for a question's threshold: per-call override > per_question
    # > per_type > default_threshold.
```

Rule: a `Verdict` whose `judge_id == producer_id` is invalid and must raise.

## Ledger (foundation)

```python
class LedgerRecord(BaseModel):
    trace_id: str
    run_id: str
    component: str                   # e.g. "p2.router", "p1.cite_check"
    backend: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float
    latency_ms: int
    timestamp: str                   # ISO 8601
    error: str | None = None         # set when the call failed; the record is still written
```

## Budget (foundation, used by P1 and P3)

```python
class Budget(BaseModel):
    max_usd: float
    max_wall_seconds: int
    max_model_calls: int | None = None
    spent_usd: float = 0.0
    elapsed_seconds: int = 0
    model_calls_used: int = 0
    # charge(usd, seconds, calls=1) raises BudgetExceeded when any limit would
    # be crossed, and leaves the budget unchanged when it raises
```

## Auditor (P1)

```python
class Location(BaseModel):
    page: int | None = None
    section: str | None = None
    table: str | None = None
    quote: str | None = None         # short excerpt only

class Claim(BaseModel):
    id: str
    kind: Literal["numeric", "citation", "method", "novelty"]
    text: str
    value: float | None = None       # numeric claims
    location: Location

class Evidence(BaseModel):
    claim_id: str
    source: Literal["paper", "bibliography_api", "repo", "log", "rerun", "prior_work"]
    reference: str                   # URL, DOI, file path + line, log line
    matched: bool | None             # None = could not determine
    detail: str | None = None

class Finding(BaseModel):
    check: Literal["citation", "numeric", "method_code", "spec_leakage", "novelty", "rerun"]
    severity: Literal["info", "warn", "fail"]
    claim_ids: list[str]
    evidence: list[Evidence]
    verdicts: list[Verdict]
    summary: str

class AuditReport(BaseModel):
    paper_id: str
    paper_source: str                # URL or path
    repo: str | None
    findings: list[Finding]
    overall: Literal["green", "amber", "red"]
    checks_run: list[str]
    checks_skipped: dict[str, str]   # check -> reason
    total_cost_usd: float
    wall_seconds: int
    schema_version: str = "0.3"      # always the current document version
```

## Research agent (P3)

```python
class StageResult(BaseModel):
    run_id: str
    stage: Literal["baseline", "ideate", "subset_exp", "full_exp",
                   "ablation", "write_up", "audit"]
    artifact_ref: str                # path/ID of produced artifact
    producer_id: str
    gate: Verdict                    # issued by a different component
    decision: Literal["accept", "refine", "reject"]
    metrics: dict[str, float] = {}
    budget_after: Budget
```

Rule: a `StageResult` is invalid and must raise when its gate is issued by the
stage's producer (`gate.judge_id == producer_id`), or when the gate names a
different artifact producer (`gate.producer_id` set and `!= producer_id`). The
`Verdict` rule alone can't catch the first case when `gate.producer_id` is empty.

## Changelog

- 0.1 — initial draft.
- 0.2 — `Budget.model_calls_used` added: without a counter, `max_model_calls`
  could not be enforced by `charge()`. `charge()` signature and no-partial-charge
  rule stated.
- 0.3 — `StageResult` no-self-grading rule: the gate's judge must differ from
  the stage's producer, and the gate's producer (if set) must match it (RSH-F-03).
- 0.4 — `RoutingPolicy.per_type` added (JDG-F-03 requires thresholds per
  question type; only per question id existed) with the precedence rule;
  `LedgerRecord.error` added so failed calls are recorded too (FND-F-01).
- 0.5 — `Verdict.confidence_source` added: the benchmark compares calibration
  of log-probability and self-reported confidence (JDG-F-06), so a verdict
  records which it has; a malformed answer has source "none" and confidence 0.
- 0.6 — `confidence_source="logprobs"` defined as the model's own probabilities,
  covering a decision model's native distribution (TypeSafe Jev) as well as
  token log-probabilities; no field change.
