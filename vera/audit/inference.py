# ruff: noqa: E501
"""The inference check (RSH-F-13, AUD-F-11, Increment 6): does an interpretation statement follow from the claims it names?

A review paper's interpretation sections (discussion, conclusions, research agenda) say what VERA reads in the verified
claims. Each statement names its premises, claim ids such as `C3`. It is checked in two layers, and the same checks run
in the paper's interpretation stage (where a failure is repaired once or removed) and again in the paper's audit:

1. **Deterministic** (`statement_problem`): at least one premise, and every premise exists; no source cited directly (`[Rn]`, a
   bare `R12`, "et al", an author-year); no named system or author (a mixed-case name such as "DRMiner") that none of
   its premises names; no number that none of its premises states.
2. **Judge** (`follows`, question `paper.inference_follows`): shown only the statement and its premise claims, does the
   statement follow without adding facts or overstating their strength? A component other than the statement's writer
   (`p3.paper.interpret`) answers it.

This module is new in Increment 6 and is not one of the audit files frozen at Increment 5; its seeded test set is
frozen (hashed) before the one run that measures it (`data/seeded_inference/`).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from vera.literature import anchoring, synthesis
from vera.schemas import Evidence, Finding, Question, QuestionType, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
PREMISE_MARKER = re.compile(r"\s*\((?:C\d+)(?:,\s*C\d+)*\)")
CLAIM_ID = re.compile(r"^C\d+$")
_NAME = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*\b")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def _names(text: str) -> set[str]:
    """Mixed-case names (DRMiner, AutoCodeRover, SWE-agent, OpenHands): a capital after the first letter and a lower-case
    letter somewhere. Plain acronyms (LLM, LLMs) and ordinary capitalised words are not names."""
    out = set()
    for w in _NAME.findall(text):
        core = w[:-1] if w.endswith("s") and w[:-1].isupper() else w
        if core.isupper() or core[1:].islower() or not any(c.isupper() for c in core[1:]):
            continue
        out.add(w)
    return out


def _numbers(text: str) -> set[str]:
    return {n.rstrip("%") for n in _NUMBER.findall(PREMISE_MARKER.sub("", text))}


def statement_problem(text: str, premises: list[str], claims: dict[str, str]) -> str | None:
    """Why a statement fails the deterministic rules, or None. `claims` maps claim id -> claim text (and source title)."""
    if not premises:
        return "no premise: an interpretation statement must name the claims it rests on"
    bad = [p for p in premises if not CLAIM_ID.match(p) or p not in claims]
    if bad:
        return f"premise does not exist: {', '.join(bad)}"
    body = PREMISE_MARKER.sub("", text)
    if synthesis.STRAY_ATTRIBUTION.search(body) or anchoring.names_a_source_without_a_claim(body):
        return "cites a source directly: interpretation may cite claims only"
    premise_text = " ".join(claims[p] for p in premises)
    unknown = sorted(n for n in _names(body) if n.lower() not in premise_text.lower())
    if unknown:
        return f"names {', '.join(unknown)}, which none of its premises names"
    figures = sorted(_numbers(body) - _numbers(premise_text))
    if figures:
        return f"states {', '.join(figures)}, which none of its premises states"
    return None


def follows(text: str, premises: list[str], claims: dict[str, str]) -> tuple[Question, str]:
    """(question, material): does the statement follow from its premise claims alone?"""
    listed = "\n".join(f"{p}: {claims[p]}" for p in premises)
    material = f"Claims (each verified against a quote from its source):\n{listed}\n\nStatement: {PREMISE_MARKER.sub('', text).strip()}"
    q = (
        "Does the statement follow from these claims alone, without adding facts, numbers, causes or generalisations "
        "they do not support, and without stating as certain or general what they only report or suggest? A cautious "
        "reading, a combination of the claims, or a gap they leave open counts as following. Answer false if the "
        "statement says more than the claims allow, contradicts them, or rests on a claim that does not bear on it."
    )
    return Question(id="paper.inference_follows", type=QuestionType.BOOLEAN, text=q), material


def check(text: str, premises: list[str], claims: dict[str, str], ask: Ask) -> tuple[str | None, list[Verdict]]:
    """Both layers: (None, verdicts) if the statement passes, else (reason, verdicts). An unsure judge is a failure."""
    problem = statement_problem(text, premises, claims)
    if problem:
        return problem, []
    q, material = follows(text, premises, claims)
    v, confident = ask(q, material)
    if not confident:
        return "judge_unsure", [v]
    if v.answer is not True:
        return "does not follow from its premises", [v]
    return None, [v]


def audit(inferences: list[dict], claims: dict[str, str], ask: Ask) -> list[Finding]:
    """Findings for a paper's kept inferences: a deterministic failure or a confident "no" is a fail, an unsure verdict a
    warn. `inferences` are `Inference` dumps; only those with status "pass" are in the text, so only those are audited."""
    findings = []
    for inf in (i for i in inferences if i.get("status") == "pass"):
        reason, verdicts = check(inf["text"], inf["premises"], claims, ask)
        if reason is None:
            continue
        severity = "warn" if reason == "judge_unsure" else "fail"
        summary = f"{inf['id']} ({inf['section']}): {reason}: {inf['text'][:140]!r}"
        findings.append(Finding(check="inference", severity=severity, claim_ids=[inf["id"]], verdicts=verdicts,
                                summary=summary, evidence=[Evidence(claim_id=inf["id"], source="log",
                                                                    reference="paper/inferences.jsonl",
                                                                    matched=False, detail=summary)]))  # fmt: skip
    return findings
