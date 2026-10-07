"""VERA data contracts. docs/03-interfaces.md is normative; these models follow it."""

from vera.schemas.app import AppConfig, RunRequest, RunStatus
from vera.schemas.auditor import AuditReport, Claim, Evidence, Finding, Location
from vera.schemas.foundation import Budget, BudgetExceeded, LedgerRecord
from vera.schemas.judge import (
    BenchmarkItem,
    JudgeBackend,
    Question,
    QuestionType,
    RoutingPolicy,
    SelfGradingError,
    Verdict,
)
from vera.schemas.literature import (
    ClaimLink,
    LiteratureSection,
    ParentCandidate,
    ParentSelection,
    RetrievalStats,
    ScopedQuestion,
    SourceRecord,
    Topic,
)
from vera.schemas.research import STAGES, FigureSpec, OutputGuidance, ProblemSpec, ProtocolSpec, RunSpec, StageResult
from vera.schemas.version import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "STAGES",
    "AppConfig",
    "AuditReport",
    "BenchmarkItem",
    "Budget",
    "BudgetExceeded",
    "Claim",
    "ClaimLink",
    "Evidence",
    "Finding",
    "JudgeBackend",
    "LedgerRecord",
    "LiteratureSection",
    "Location",
    "OutputGuidance",
    "ProblemSpec",
    "Question",
    "QuestionType",
    "RoutingPolicy",
    "RunSpec",
    "ParentCandidate",
    "ParentSelection",
    "FigureSpec",
    "ProtocolSpec",
    "RetrievalStats",
    "ScopedQuestion",
    "SelfGradingError",
    "SourceRecord",
    "RunRequest",
    "RunStatus",
    "StageResult",
    "Topic",
    "Verdict",
]
