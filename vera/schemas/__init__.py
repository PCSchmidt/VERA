"""VERA data contracts. docs/03-interfaces.md is normative; these models follow it."""

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
from vera.schemas.research import STAGES, OutputGuidance, ProblemSpec, RunSpec, StageResult
from vera.schemas.version import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "STAGES",
    "AuditReport",
    "BenchmarkItem",
    "Budget",
    "BudgetExceeded",
    "Claim",
    "Evidence",
    "Finding",
    "JudgeBackend",
    "LedgerRecord",
    "Location",
    "OutputGuidance",
    "ProblemSpec",
    "Question",
    "QuestionType",
    "RoutingPolicy",
    "RunSpec",
    "SelfGradingError",
    "StageResult",
    "Verdict",
]
