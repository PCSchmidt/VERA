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
