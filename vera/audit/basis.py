# ruff: noqa: E501
"""The reproduction basis (Increment 4): the paper must say which row set the baseline was reproduced on, as registered.

The registered target says, per dataset, whether the baseline is compared with the parent's number on held-out or in-sample
rows (`datasets.<name>.reproduction_metric`). A paper that states a basis for a dataset that differs from the registered one
is a `fail` (it misdescribes what the reproduction was); a paper that mentions the reproduction and states no basis at all is a
`warn`; a paper with no reproduction statement is not checked (older write-ups). A statement is a sentence with "reproduc" in
it and the word in-sample or held-out; a dataset is named by its label in that sentence or in the one before it.
"""

from __future__ import annotations

import re

from vera.audit.numbers import sentences
from vera.loop import tables
from vera.schemas import Claim, Evidence, Finding, Location

IN_SAMPLE = re.compile(r"in[- ]sample|training data|training rows", re.IGNORECASE)
HELD_OUT = re.compile(r"held[- ]out|test set|out[- ]of[- ]sample", re.IGNORECASE)


def registered_basis(target: dict | None) -> dict[str, str]:
    """dataset -> "in-sample" | "held-out", from the registered target (empty when it names none)."""
    out = {}
    for name, entry in ((target or {}).get("datasets") or {}).items():
        metric = entry.get("reproduction_metric") if isinstance(entry, dict) else None
        if metric:
            out[name] = "in-sample" if "in_sample" in metric else "held-out"
    return out


def audit_basis(text: str, results_json: dict, target: dict | None) -> tuple[list[Claim], list[Finding]]:
    claims: list[Claim] = []
    findings: list[Finding] = []
    registered = registered_basis(target)
    datasets = [d for d in results_json.get("datasets", []) if d in registered]
    if not datasets:
        return claims, findings
    sents = [s for _, s in sentences(text)]
    stated = [
        i
        for i, s in enumerate(sents)
        if re.search(r"reproduc", s, re.IGNORECASE) and (IN_SAMPLE.search(s) or HELD_OUT.search(s))
    ]
    mentions = any(re.search(r"reproduc", s, re.IGNORECASE) for s in sents)
    if not stated:
        if mentions:
            claim = Claim(
                id="basis:none", kind="numeric", text="the reproduction statement", location=Location(section="Method")
            )
            claims.append(claim)
            findings.append(
                _finding(
                    "warn",
                    claim,
                    "The paper mentions the baseline reproduction but does not say whether it was made on held-out or in-sample rows.",
                )
            )
        return claims, findings
    for i in stated:
        s = sents[i]
        context = f"{sents[i - 1]} {s}" if i else s
        for d in datasets:
            label = tables.dataset_label(d)
            if not re.search(rf"(?<!\w){re.escape(label)}(?!\w)", context, re.IGNORECASE):
                continue
            window = s if re.search(rf"(?<!\w){re.escape(label)}(?!\w)", s, re.IGNORECASE) else context
            says = (
                "in-sample"
                if IN_SAMPLE.search(window) and not HELD_OUT.search(window)
                else "held-out"
                if HELD_OUT.search(window) and not IN_SAMPLE.search(window)
                else None
            )
            if says is None:
                continue  # both words in the window: the sentence contrasts the two, nothing to compare
            claim = Claim(
                id=f"basis:{d}:{i}", kind="numeric", text=s, location=Location(section="Method", quote=s[:200])
            )
            claims.append(claim)
            if says != registered[d]:
                findings.append(
                    _finding(
                        "fail",
                        claim,
                        f"The paper says the baseline was reproduced on {says} rows for {label}; the registered target compares {registered[d]} rows: {s[:160]!r}",
                    )
                )
    return claims, findings


def _finding(severity: str, claim: Claim, summary: str) -> Finding:
    return Finding(check="numeric", severity=severity, claim_ids=[claim.id], verdicts=[], summary=summary,
                   evidence=[Evidence(claim_id=claim.id, source="log", reference="registered target: reproduction_metric", matched=False, detail=summary)])  # fmt: skip
