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
from vera.schemas.research import StageResult
from vera.schemas.version import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
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
    "Question",
    "QuestionType",
    "RoutingPolicy",
    "SelfGradingError",
    "StageResult",
    "Verdict",
]
