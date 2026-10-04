# ruff: noqa: E501
"""AUD-F-05, method-code alignment (Increment 4): does the paper describe what the code does, and the code do what the paper says?

For each idea whose code the run kept and whose name the paper's Method section uses, two kinds of question go to the judge
(the cheap path, never the producer of the text):

- for each *sentence* of the Method paragraphs that describe the idea: does the code implement what it says? A described step
  with no code is a `warn` finding (`method_code`): the paper claims a computation that was not run;
- for each *substantial function* of the code (three statements or more): does the paper's description cover what it does? A
  function the paper does not describe is a `warn` finding: the run computes something the paper does not say.

The judge sees the code excerpt and the paper's words, not the results. The registered harness is the reference method's code
and is trusted, so it is not audited here; the loop's `method.py` modules are. Findings are `warn`, not `fail`: a judge's
reading of code against prose is a lead for a person, which the review states.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable

from vera.audit.alignment import aliases
from vera.audit.numbers import sentences
from vera.schemas import Claim, Evidence, Finding, Location, Question, QuestionType, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
MIN_STATEMENTS = 3
MAX_COMPONENTS = 6


def code_components(code: str) -> list[dict]:
    """The substantial functions of a module: [{"name", "source"}], outermost first (a nested function is its own entry)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            body = [n for n in ast.walk(node) if isinstance(n, ast.stmt)]
            if len(body) - 1 >= MIN_STATEMENTS:
                out.append({"name": node.name, "source": ast.get_source_segment(code, node) or ""})
    return out[:MAX_COMPONENTS]


def method_section(text: str) -> str:
    body = text.partition("## References")[0]
    m = re.search(r"^#{1,6}\s*(?:\d+\.?\s*)?(?:Method|Approach)\b.*?$(.*?)(?=^#{1,6}\s|\Z)", body, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def idea_paragraphs(method: str, idea: str) -> list[str]:
    """The Method paragraphs that name the idea (by its label, its code or its name)."""
    words = aliases(idea)
    return [p for p in re.split(r"\n\s*\n", method) if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", p, re.IGNORECASE) for w in words)]


def audit_method_code(text: str, methods: dict[str, str], ask: Ask) -> tuple[list[Claim], list[Finding]]:
    """`methods`: idea name -> the code of its valid run. Returns the claims checked and the findings."""
    claims: list[Claim] = []
    findings: list[Finding] = []
    method = method_section(text)
    for idea, code in methods.items():
        paras = idea_paragraphs(method, idea)
        if not paras:
            continue  # the paper's Method does not describe this idea: nothing to align (the audit says so in its checks)
        described = "\n\n".join(paras)
        steps = [s for _, s in sentences("## Method\n\n" + described)]
        for n, step in enumerate(steps):
            claim = Claim(id=f"code:{idea}:step{n}", kind="method", text=step,
                          location=Location(section="Method", quote=step[:200]))  # fmt: skip
            claims.append(claim)
            question = Question(
                id="audit.code_implements_step", type=QuestionType.BOOLEAN,
                text=("Does the code implement what this sentence of the paper says the method does? Answer false if the "
                      f"sentence describes a computation, parameter or choice that the code does not perform. Sentence: {step}"),
            )  # fmt: skip
            verdict, confident = ask(question, f"Code of the method:\n```python\n{code}\n```")
            if confident and verdict.answer is False:
                findings.append(_finding(claim, f"The paper says: {step[:160]!r}, and the code of {idea} does not do it.", verdict))
        for comp in code_components(code):
            claim = Claim(id=f"code:{idea}:{comp['name']}", kind="method", text=f"function {comp['name']}",
                          location=Location(section="Method", quote=comp["source"][:200]))  # fmt: skip
            claims.append(claim)
            question = Question(
                id="audit.paper_describes_code", type=QuestionType.BOOLEAN,
                text=("Does the paper's description of the method cover what this function of its code does? Answer false if "
                      "the function performs a step, transformation or choice that the description does not mention."),
            )  # fmt: skip
            verdict, confident = ask(question, f"Paper's description of {idea}:\n{described}\n\nFunction `{comp['name']}`:\n```python\n{comp['source']}\n```")
            if confident and verdict.answer is False:
                findings.append(_finding(claim, f"The code of {idea} has a function {comp['name']!r} that the paper does not describe.", verdict))
    return claims, findings


def _finding(claim: Claim, summary: str, verdict: Verdict) -> Finding:
    return Finding(check="method_code", severity="warn", claim_ids=[claim.id], verdicts=[verdict], summary=summary,
                   evidence=[Evidence(claim_id=claim.id, source="repo", reference="method.py", matched=False, detail=summary)])  # fmt: skip
