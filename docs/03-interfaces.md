# 03 — Interfaces (core schemas)

Version 0.9 · Draft · Changes require a version bump and a changelog line.

These are the contracts between layers. Implement as Pydantic v2 models in
`vera/schemas/`. Field lists are normative; the Python below is a sketch.

## Judge layer (P2)

```python
from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    CHOICE = "choice"  # pick one of `options`
    SCORE = "score"  # integer on a rubric scale
    BOOLEAN = "boolean"  # true/false with probability


class Question(BaseModel):
    id: str  # stable ID, e.g. "aud.cite.exists"
    type: QuestionType
    text: str  # one atomic question
    options: list[str] | None = None  # CHOICE only
    scale: tuple[int, int] | None = None  # SCORE only, e.g. (1, 5)
    rubric: str | None = None  # SCORE guidance


class Verdict(BaseModel):
    question_id: str
    answer: str | int | bool
    probabilities: dict[str, float] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_source: Literal["logprobs", "self_report", "none"] | None = None
    # where confidence came from: "logprobs" = the model's own probabilities
    # (token log-probabilities, or a decision model's native distribution);
    # "self_report" = probability the model states; "none" = malformed (confidence 0)
    backend: str  # which backend produced the final answer
    escalated: bool  # True if any cheaper backend was bypassed
    cost_usd: float
    latency_ms: int
    trace_id: str
    producer_id: str | None = None  # component that produced the judged artifact
    judge_id: str  # component issuing this verdict (must != producer_id)


class JudgeBackend(Protocol):
    name: str
    cost_rank: int  # lower = tried first

    def ask(self, state: str, questions: list[Question]) -> list[Verdict]: ...


class RoutingPolicy(BaseModel):
    default_threshold: float = 0.7
    per_type: dict[QuestionType, float] = {}  # per question type (JDG-F-03)
    per_question: dict[str, float] = {}  # per question id; overrides per_type
    max_escalations: int = 1
    # Precedence for a question's threshold: per-call override > per_question
    # > per_type > default_threshold.
```

Rule: a `Verdict` whose `judge_id == producer_id` is invalid and must raise.

### Benchmark items (P2 evaluation)

```python
class BenchmarkItem(BaseModel):
    id: str  # stable, e.g. "cite-0042"
    task: Literal["loop_gate", "numeric", "citation", "claim_support"]
    split: Literal["dev", "test"]  # dev = tuning; test = reporting only (docs/06 §5)
    question: Question
    state: str  # the material the judge sees
    label: str | int | bool  # correct answer, known from how the item was built
    construction: dict[str, str | int | float | bool]
    # how it was built: kind (e.g. "true", "digit_change",
    # "near_miss_title"), source (paper id, table no.), seed
    generator: str  # generator name and version that built it
```

Rule: `label` must be a valid answer to `question` (a bool for Boolean, one of
`options` for Choice, an integer inside `scale` for Score); an invalid label
raises. Items live in `data/benchmark/items.jsonl`; the split and the test
split's SHA-256 (over the test items' JSON lines, sorted by id) are recorded in
`data/benchmark/split.json` before any backend sees the test split.

## Ledger (foundation)

```python
class LedgerRecord(BaseModel):
    trace_id: str
    run_id: str
    component: str  # e.g. "p2.router", "p1.cite_check"
    backend: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float
    latency_ms: int
    timestamp: str  # ISO 8601
    error: str | None = None  # set when the call failed; the record is still written
    provider: str | None = None  # serving provider the API reports (e.g. OpenRouter's); None if unknown
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
    schema_version: str = "0.3"  # always the current document version
```

## Research agent (P3)

```python
class StageResult(BaseModel):
    run_id: str
    stage: Literal["scope", "retrieve", "read", "synthesize", "parent",
                   "baseline", "ideate", "subset_exp", "full_exp", "ablation", "write_up", "audit"]
    artifact_ref: str  # path/ID of produced artifact
    producer_id: str
    gates: list[Verdict]  # every verdict the stage asked (at least one), each from a different component
    deciding_gates: list[int] = []  # indices into `gates` of the verdicts that caused a reject or refine
    reason: str | None = None  # a deterministic cause of a reject, when no verdict decided it
    decision: Literal["accept", "refine", "reject"]
    metrics: dict[str, float] = {}
    budget_after: Budget
    # property `gate`: gates[deciding_gates[0]] if any, else gates[0]
```

Rules (0.9): every verdict in `gates` obeys the no-self-grading rule below;
`deciding_gates` indices must exist; a `reject` must name a deciding verdict or a
`reason` (the Increment 2 experiments stage stored its first verdict, a "yes",
on a rejected stage). A record stored with the 0.8 single `gate` loads as
`gates=[gate]`, with `deciding_gates=[0]` unless it was an accept.

### Literature stage (RSH-F-08, RSH-F-09, AUD-F-10; 0.9)

```python
class Topic(BaseModel):
    id: str  # filename-safe, as run_id
    text: str  # non-empty
    key_papers_ref: str | None = None  # data/topics/<id>.json: the recall measure for retrieval
    scope_hint: str | None = None  # the user's note on the path and what a good question looks like (never key papers)


class ScopedQuestion(BaseModel):
    topic_id: str
    question: str
    why_researchable: str
    empirical: bool
    candidate_parent: str | None = None  # arXiv id or DOI; none for a non-empirical question
    no_parent_reason: str | None = None
    status: Literal["proposed", "confirmed", "edited"] = "proposed"
    confirmed_by: str | None = None  # required when status != "proposed", and only then
    confirmed_at: str | None = None  # ISO 8601 UTC


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
    retrieved: str | None = None


class ClaimLink(BaseModel):
    claim: str
    source_key: str  # a SourceRecord.key
    quote: str  # non-blank: a verbatim (normalised) span of the source's text
    locator: str  # "abstract", "sec. 3", a passage id
    quote_check: Literal["pass", "fail", "unchecked"] = "unchecked"  # deterministic
    verdicts: list[Verdict] = []  # lit.claim_supported, from a component other than the producer


class LiteratureSection(BaseModel):
    run_id: str
    topic_id: str
    text: str  # cites [Rn]
    claims: list[ClaimLink]  # every claim's source_key is in `sources`
    sources: list[SourceRecord]
```

```python
class ParentCandidate(BaseModel):  # RSH-F-10: one repository found in a paper the stage read
    source_key: str  # the retrieved paper it came from (Rn)
    paper_id: str
    title: str
    repo_url: str
    repo_resolves: bool  # looked up live (GitHub API), never from model text
    licence: str | None = None  # SPDX id the host reports
    pushed_at: str | None = None
    archived: bool = False
    own_code: Literal["yes", "no", "unclear"] = "unclear"  # does the paper present it as its own code
    url_context: str = ""  # the sentence of the paper that names it
    datasets: list[str] = []
    compute: str = ""
    compute_basis: Literal["stated", "inferred", "unknown"] = "unknown"
    cpu_minutes: float | None = None  # the model's estimate for one baseline replication on CPU
    harness_in_docker: str | None = None  # the docker/ directory whose Dockerfile builds this repository
    notes: str = ""


class ParentSelection(BaseModel):  # data/topics/parent_<topic>.json
    run_id: str
    topic_id: str
    question: str
    candidates: list[ParentCandidate]
    picked: str | None = None  # a candidate's repo_url
    none_fits_reason: str | None = None  # exactly one of `picked` and `none_fits_reason` is set
    verdicts: list[Verdict] = []  # lit.parent_fits per candidate judged; lit.parent_refusal when nothing was picked
    user_review: dict | None = None  # {"right": bool, "note": str, "by": str, "at": str}: the user's reading
```

The repository URLs come from a regular expression over the papers' PDF text and link annotations, and each is
looked up live; the model fills only what the paper says (own code, datasets, compute). A refusal is itself sent to
the judge (`lit.parent_refusal`); a doubted refusal rejects the stage.

`RunSpec.topic: Topic | None = None` is set when a run starts from a topic; a `RunSpec` needs a
`problem`, a `topic`, or both (a literature-only run has no problem).

### Run specification (RSH-F-01)

```python
class ProblemSpec(BaseModel):
    parent_id: str  # arXiv id or DOI of the parent paper
    repo_url: str  # parent code
    repo_commit: str  # pinned commit, 40 hex characters
    metric: str  # the quality metric the loop optimises, e.g. "decomposition_residual"
    datasets: list[str]  # non-empty
    subset: dict[str, int | float | str] = {}  # e.g. {"n_samples": 1000, "n_trees": 50}


class OutputGuidance(BaseModel):
    format: str = "paper"  # target format
    max_words: int | None = None
    required_sections: list[str] = []
    emphasis: str | None = None
    constraints: list[str] = []  # plain-language rules the final check enforces


class RunSpec(BaseModel):
    run_id: str  # filename-safe; names the run's ledger and checkpoint files
    problem: ProblemSpec | None = None  # none until a parent problem is chosen (topic runs, 0.9)
    guidance: OutputGuidance
    budget: Budget  # spent counters start at zero
    models: dict[str, str] = {}  # stage -> backend name; stage names as in StageResult.stage
```

Rules: `run_id` matches `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`; `repo_commit` is 40 hex
characters; `datasets` is non-empty; `budget.max_usd` is positive and nothing is
spent yet; `models` keys are stage names. An invalid spec raises.

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
- 0.7 — `BenchmarkItem` added (Increment 1 benchmark, risk R3): each item
  carries its label and how it was built, so labels are known by construction
  and a label that isn't a valid answer to its question raises.
- 0.8 — `LedgerRecord.provider` added: OpenRouter serves one model through many
  providers at different prices, so per-provider cost and quality could not be
  separated (Increment 1 open item). `RunSpec`, `ProblemSpec` and `OutputGuidance`
  added for the research loop's inputs (RSH-F-01, Increment 2).
- 0.9 — `Finding.check` gains `"claim_support"` (AUD-F-10); `BenchmarkItem.task` gains `"claim_support"` (the literature stage's `lit.claim_supported`
  benchmark). Literature stage types (`Topic`, `ScopedQuestion`, `SourceRecord`,
  `ClaimLink`, `LiteratureSection`, `RunSpec.topic`) and new stage names.
  `StageResult.gate` becomes `gates` plus `deciding_gates` and `reason`: the
  Increment 2 experiments stage asked four "beats baseline?" questions but
  stored the first (a "yes") on a rejected stage. Records stored with a single
  `gate` still load.
