"""The literature stage's judge questions. Ids start with `lit.`: see `vera.loop.LIT_PREFIX` for their routing."""

from __future__ import annotations

from vera.schemas import Question, QuestionType, ScopedQuestion


def question_scoped(topic_text: str, scoped: ScopedQuestion) -> tuple[Question, str]:
    """(question, material): is the proposed question one researchable question, not a restatement of the topic?"""
    material = (
        f"Topic: {topic_text}\n\n"
        f"Proposed research question: {scoped.question}\n"
        f"Why it is researchable: {scoped.why_researchable}\n"
        f"Empirical: {'yes' if scoped.empirical else 'no'}"
        + (f"\nCandidate parent problem: {scoped.candidate_parent}" if scoped.candidate_parent else "")
        + (f"\nWhy no parent problem: {scoped.no_parent_reason}" if scoped.no_parent_reason else "")
    )
    question = Question(
        id="lit.question_scoped",
        type=QuestionType.BOOLEAN,
        text=(
            "Is the proposed research question a single, specific question that could be answered by a short "
            "literature review (and, if marked empirical, by small CPU-scale experiments of minutes each), and not "
            "merely a restatement of the topic? Answer false if it asks several things at once, is too vague to "
            "tell when it has been answered, or needs resources beyond a laptop CPU while marked empirical."
        ),
    )
    return question, material


def relevant(question: str, record: dict) -> tuple[Question, str]:
    """(question, material): does this record bear on the scoped question? Judged on the title and abstract only."""
    abstract = (record.get("abstract") or "").strip()
    material = (
        f"Research question: {question}\n\n"
        f"Candidate paper: {record['title']} ({record.get('year') or 'n.d.'})\n"
        + (f"Abstract: {abstract[:1800]}" if abstract else "Abstract: (not available; judge from the title alone)")
    )
    text = (
        "Does this candidate paper bear directly on the research question, so that a literature review of the "
        "question should read it? Answer false if it is only loosely related, about a different problem that shares "
        "a keyword, or too general to inform the question."
    )
    return Question(id="lit.relevant", type=QuestionType.BOOLEAN, text=text), material


def evidence_sufficient(question: str, papers: list[dict]) -> tuple[Question, str]:
    """(question, material): is the evidence gathered enough to write a literature section on the question?

    `papers` carry a title, how the paper was read ("fulltext" or "abstract") and its best passage."""
    lines = []
    for p in papers:
        lines.append(f"- {p['title']} ({p['mode']}): {p['best'][:240]}")
    material = f"Research question: {question}\n\nEvidence gathered ({len(papers)} papers):\n" + "\n".join(lines)
    text = (
        "Is the evidence gathered (the papers listed and the passages quoted from them) enough to write a short "
        "literature section that bears on the research question, saying what the sources establish and where they "
        "stop? Answer false if most of the evidence is about something else, or too thin to support a section."
    )
    return Question(id="lit.evidence_sufficient", type=QuestionType.BOOLEAN, text=text), material
