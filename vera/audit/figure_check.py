# ruff: noqa: E501
"""Audit of a paper's figures against results.json (Increment 4, writeup2_ready).

Each figure VERA draws comes with the data it plotted (`vera.loop.figures`). A figure is a `fail` if a plotted point differs
from the results.json cell it names, if it names a cell that does not exist, or if the paper shows an image no record
describes (a figure VERA did not draw). A paper whose figures all agree adds nothing (the report's `checks_run` lists `figure`).
"""

from __future__ import annotations

import re

from vera.loop import figures
from vera.schemas import Claim, Evidence, Finding, Location


def audit_figures(text: str, results_json: dict, records: list[dict]) -> tuple[list[Claim], list[Finding]]:
    claims: list[Claim] = []
    findings: list[Finding] = []
    known = {rec["file"] for rec in records}
    shown = set(re.findall(r"!\[[^\]]*\]\(figures/([^)]+)\)", text.partition("## References")[0]))
    for rec in records:
        claim = Claim(id=f"fig:{rec['id']}", kind="numeric", text=f"{rec['id']}: {rec['title']}",
                      location=Location(section="Results", table=rec["id"], quote=rec["title"][:200]))  # fmt: skip
        claims.append(claim)
        for problem in figures.check_data(results_json, [rec]):
            findings.append(_finding("fail", claim, rec["id"], problem))
    for stray in sorted(shown - known):
        claim = Claim(id=f"fig:{stray}", kind="numeric", text=f"image {stray}", location=Location(section="Results"))
        claims.append(claim)
        findings.append(_finding("fail", claim, stray, f"the paper shows figures/{stray}, which VERA did not draw"))
    return claims, findings


def _finding(severity: str, claim: Claim, reference: str, summary: str) -> Finding:
    return Finding(check="numeric", severity=severity, claim_ids=[claim.id], verdicts=[], summary=summary,
                   evidence=[Evidence(claim_id=claim.id, source="log", reference=f"figures.json:{reference}",
                                      matched=severity == "info", detail=summary)])  # fmt: skip
