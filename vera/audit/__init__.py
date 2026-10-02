"""Minimal P1 (Increment 2): the loop's final gate. Citation existence and numeric consistency of the write-up
against the run's own retrieval log and results, with evidence for every finding.

`run_audit` returns the `AuditReport` of docs/03. Overall status: red if any finding is a `fail`, amber if any is a
`warn` (something could not be confirmed), else green. A red audit blocks "success" (RSH-F-05); the loop stage that
calls this is `vera.loop.audit_stage`. Checks that need more than the run's own logs are listed as skipped, with
the increment that adds them, rather than silently absent.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from vera.audit.citations import audit_citations
from vera.audit.numbers import audit_numbers
from vera.schemas import AuditReport, Claim, Finding, Question, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]

SKIPPED = {
    "method_code": "AUD-F-05: method-code alignment arrives in Increment 4",
    "spec_leakage": "AUD-F-06: leakage checks arrive in Increment 6",
    "novelty": "AUD-F-07: novelty against retrieved literature arrives in Increment 4",
    "rerun": "AUD-F-08: re-running experiments is optional, Increment 6",
}


@dataclass
class AuditRun:
    report: AuditReport
    claims: list[Claim]


def overall_of(findings: list[Finding]) -> str:
    if any(f.severity == "fail" for f in findings):
        return "red"
    return "amber" if any(f.severity == "warn" for f in findings) else "green"


def run_audit(
    text: str,
    results_json: dict,
    retrieved: list[dict],
    *,
    ask: Ask,
    lookup: Callable[[str], list[dict]],
    paper_id: str,
    paper_source: str,
    target: dict | None = None,
) -> AuditRun:
    start = time.perf_counter()
    cost = [0.0]

    def metered(question: Question, material: str) -> tuple[Verdict, bool]:
        verdict, confident = ask(question, material)
        cost[0] += verdict.cost_usd
        return verdict, confident

    cite_claims, cite_findings = audit_citations(text, retrieved, metered, lookup)
    num_claims, num_findings = audit_numbers(text, results_json, metered, target)
    findings = [*cite_findings, *num_findings]
    report = AuditReport(
        paper_id=paper_id,
        paper_source=paper_source,
        repo=None,
        findings=findings,
        overall=overall_of(findings),
        checks_run=["citation", "numeric"],
        checks_skipped=dict(SKIPPED),
        total_cost_usd=cost[0],
        wall_seconds=round(time.perf_counter() - start),
    )
    return AuditRun(report, [*cite_claims, *num_claims])


def render_markdown(run: AuditRun) -> str:
    r = run.report
    lines = [
        f"# Audit of {r.paper_id}: **{r.overall.upper()}**",
        "",
        f"Checks run: {', '.join(r.checks_run)}. Claims checked: {len(run.claims)}. "
        f"Findings: {sum(f.severity == 'fail' for f in r.findings)} fail, "
        f"{sum(f.severity == 'warn' for f in r.findings)} warn, "
        f"{sum(f.severity == 'info' for f in r.findings)} info. Judge cost ${r.total_cost_usd:.5f}.",
        "",
    ]
    for f in r.findings:
        lines.append(f"- **{f.severity}** ({f.check}) {f.summary}")
        lines += [f"  - evidence: {e.source} `{e.reference}` matched={e.matched}" for e in f.evidence]
    if not r.findings:
        lines.append("No findings.")
    lines += ["", "Skipped checks:"] + [f"- {k}: {v}" for k, v in r.checks_skipped.items()]
    return "\n".join(lines) + "\n"
