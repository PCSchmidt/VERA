# ruff: noqa: E501
"""AUD-F-07, novelty (Increment 4): is the loop's idea materially distinct from the closest prior work?

For each idea the run kept, the closest prior work is found two ways: the literature stage's own retrieval records (ranked
by the overlap of their title and abstract with the idea's description, tf-idf cosine, nothing the model decides) and, when a
`search` function is supplied, one targeted search with the idea's description as the query. The judge (the cheap path, shown
the idea and one prior work's title and abstract, never the paper's results) says whether the idea's core method is materially
distinct from that work's method. A "not distinct" verdict is a `warn` finding naming the prior work: a finding, never a block.

`judge_pair` is the one question, used by the gold-set measurement (`data/novelty_gold/`: ideas paired with known prior methods,
labelled distinct or not distinct) as well as by the audit, so the measured behaviour is the audited behaviour.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable

from vera.schemas import Claim, Evidence, Finding, Location, Question, QuestionType, Verdict

Ask = Callable[[Question, str], tuple[Verdict, bool]]
TOP_K = 3
STOP = set("the a an of and or to in for on with by is are as at from that this these those it its be can we our their using use via based".split())


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()) if w not in STOP]


def closest(idea: str, records: list[dict], k: int = TOP_K) -> list[dict]:
    """The `k` records whose title and abstract overlap the idea's description most (tf-idf cosine over the records)."""
    docs = [Counter(tokens(f"{r.get('title', '')} {r.get('abstract', '')}")) for r in records]
    df = Counter(w for d in docs for w in d)
    n = max(len(docs), 1)

    def vec(c: Counter) -> dict[str, float]:
        return {w: tf * math.log(1 + n / df.get(w, 1)) for w, tf in c.items()}

    q = vec(Counter(tokens(idea)))
    qn = math.sqrt(sum(v * v for v in q.values())) or 1.0
    scored = []
    for r, d in zip(records, docs, strict=True):
        v = vec(d)
        dot = sum(q[w] * v[w] for w in q if w in v)
        scored.append((dot / (qn * (math.sqrt(sum(x * x for x in v.values())) or 1.0)), r))
    return [r for s, r in sorted(scored, key=lambda t: -t[0])[:k] if s > 0]


def judge_pair(idea: str, prior_title: str, prior_text: str, ask: Ask) -> tuple[bool | None, Verdict]:
    """(distinct?, the verdict): True/False when the judge is confident, None when it is not."""
    question = Question(
        id="audit.novelty_distinct", type=QuestionType.BOOLEAN,
        text=("Is the core method of the proposed idea materially distinct from the prior work's method? Answer false if the "
              "idea is that method, possibly renamed, reworded or with a small variation, and true if it is a different "
              "method or approach."),
    )  # fmt: skip
    material = f"Proposed idea:\n{idea}\n\nPrior work: {prior_title}\n{prior_text[:1500]}"
    verdict, confident = ask(question, material)
    return (verdict.answer if confident and isinstance(verdict.answer, bool) else None), verdict


def audit_novelty(ideas: dict[str, str], records: list[dict], ask: Ask, search: Callable[[str], list[dict]] | None = None) -> tuple[list[Claim], list[Finding]]:
    """`ideas`: name -> description. One claim per idea; a `warn` finding per prior work judged not distinct."""
    claims: list[Claim] = []
    findings: list[Finding] = []
    for name, description in ideas.items():
        claim = Claim(id=f"novelty:{name}", kind="novelty", text=f"{name}: {description}"[:300],
                      location=Location(section="Method", quote=description[:200]))  # fmt: skip
        claims.append(claim)
        pool = list(records)
        if search is not None:
            try:
                pool += search(description)[:5]
            except Exception:  # noqa: BLE001 - a failed search leaves the retrieved records as the pool
                pass
        for prior in closest(f"{name}. {description}", pool):
            distinct, verdict = judge_pair(f"{name}: {description}", prior.get("title", ""), prior.get("abstract", ""), ask)
            if distinct is False:
                summary = f"{name} may not be materially distinct from prior work: {prior.get('title', '')!r}."
                findings.append(Finding(check="novelty", severity="warn", claim_ids=[claim.id], verdicts=[verdict], summary=summary,
                                        evidence=[Evidence(claim_id=claim.id, source="prior_work", reference=prior.get("url") or prior.get("id") or prior.get("title", ""),
                                                           matched=False, detail=summary)]))  # fmt: skip
    return claims, findings
