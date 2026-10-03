"""Judge questions of the parent-selection stage (`lit.parent_*`); `questions.py` is part of the frozen audit."""

from __future__ import annotations

from vera.schemas import Question, QuestionType


def parent_fits(question: str, c) -> tuple[Question, str]:
    """(question, material): could this candidate's baseline be reproduced within the loop's limits?"""
    minutes = c.cpu_minutes if c.cpu_minutes is not None else "unknown"
    material = (
        f"Research question: {question}\n\n"
        f"Candidate parent: {c.title} ({c.paper_id})\n"
        f"Repository: {c.repo_url} (resolves: {'yes' if c.repo_resolves else 'no'}; "
        f"licence: {c.licence or 'none recorded'}; last push {c.pushed_at or 'unknown'}; "
        f"presented as the paper's own code: {c.own_code})\n"
        f"Datasets: {', '.join(c.datasets) or 'none identified'}\n"
        f"Compute ({c.compute_basis}): {c.compute or 'unknown'}; estimated {minutes} minutes per replication "
        "on a laptop CPU\n"
        f"Sentence of the paper that names the repository: {c.url_context}"
    )
    text = (
        "Could this candidate serve as the parent problem for the research question: its public code is the baseline, "
        "its datasets are public and small, and a replication of the baseline runs on a laptop CPU in minutes? Answer "
        "false if the code is not the paper's own, the datasets are private or large, the compute is unknown or beyond "
        "a laptop, or the baseline has little to do with the question."
    )
    return Question(id="lit.parent_fits", type=QuestionType.BOOLEAN, text=text), material


def parent_refusal(question: str, candidates: list, reasons: list[str]) -> tuple[Question, str]:
    """(question, material): is it right that no candidate can serve as the parent problem?"""
    listed = "\n".join(f"- {c.repo_url} ({c.title})" for c in candidates) or "(no candidate repository was found)"
    why = "\n".join(f"- {r}" for r in reasons)
    material = f"Research question: {question}\n\nCandidates found:\n{listed}\n\nWhy each was refused:\n{why}"
    text = (
        "A parent problem needs public code that is the paper's own, public small datasets and a baseline that runs "
        "on a laptop CPU in minutes. Given the reasons listed, is it correct that none of the candidates can serve as "
        "the parent problem? Answer false if a refusal looks mistaken, for example because a stated reason is "
        "contradicted by the other facts."
    )
    return Question(id="lit.parent_refusal", type=QuestionType.BOOLEAN, text=text), material
