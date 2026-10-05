# ruff: noqa: E501
"""Audit v3 (Increment 4): method-code alignment (AUD-F-05), novelty (AUD-F-07) and the reproduction basis. No network."""

from __future__ import annotations

from vera.audit.basis import audit_basis, registered_basis
from vera.audit.method_code import audit_method_code, code_components, idea_paragraphs, method_section
from vera.audit.novelty import audit_novelty, closest
from vera.schemas import Question, Verdict

CODE = '''import numpy as np


def helper(x):
    return x


def decompose(model, X_train, X_test):
    depth = 3
    best = None
    for d in range(1, depth + 1):
        best = d
    return 0.0, {(0,): np.zeros(len(X_test))}
'''
PAPER = """## Abstract

A.

## Method

The baseline is TreeHFD.

C2: Deeper variable selection tries depth_variable from 1 to 3 and keeps the best one. It then refits each component by isotonic regression.

## Results

R.
"""


class Judge:
    def __init__(self, answers: dict[str, bool] | None = None, default: bool = True) -> None:
        self.answers, self.default, self.asked = answers or {}, default, []

    def __call__(self, question: Question, material: str) -> tuple[Verdict, bool]:
        self.asked.append((question.id, material))
        answer = self.answers.get(question.id, self.default)
        for key, value in self.answers.items():  # a question text can also decide: "isotonic" is not in the code
            if key.startswith("text:") and key[5:] in question.text:
                answer = value
        v = Verdict(question_id=question.id, answer=answer, confidence=0.9, confidence_source="self_report", backend="fake",
                    escalated=False, cost_usd=0.0, latency_ms=1, trace_id="t", producer_id="p", judge_id="j")
        return v, True


def test_AUD_F_05_code_components_are_the_substantial_functions() -> None:
    assert [c["name"] for c in code_components(CODE)] == ["decompose"]  # helper has one statement
    assert code_components("def broken(:") == []


def test_the_method_section_and_the_paragraphs_that_name_an_idea() -> None:
    assert method_section(PAPER).startswith("The baseline is TreeHFD.")
    paras = idea_paragraphs(method_section(PAPER), "C2: Deeper variable selection")
    assert len(paras) == 1 and "isotonic" in paras[0]


def test_AUD_F_05_a_described_step_the_code_does_not_perform_is_a_finding() -> None:
    judge = Judge({"text:isotonic": False})
    claims, findings = audit_method_code(PAPER, {"C2: Deeper variable selection": CODE}, judge)
    assert [f.check for f in findings] == ["method_code"] and "isotonic" in findings[0].summary
    assert findings[0].severity == "warn" and len(claims) >= 3  # two sentences and one function


def test_a_function_the_paper_does_not_describe_is_a_finding() -> None:
    judge = Judge({"audit.paper_describes_code": False})
    _, findings = audit_method_code(PAPER, {"C2: Deeper variable selection": CODE}, judge)
    assert any("does not describe" in f.summary for f in findings)


def test_an_idea_the_method_section_does_not_name_is_not_aligned() -> None:
    claims, findings = audit_method_code(PAPER, {"C9: Unrelated": CODE}, Judge(default=False))
    assert claims == [] and findings == []


TARGET = {"datasets": {"analytical": {"reproduction_metric": "residual_mse_pct"}, "airfoil": {"reproduction_metric": "residual_in_sample_pct"}}}
RESULTS = {"datasets": ["analytical", "airfoil"]}


def test_the_registered_basis_comes_from_the_target() -> None:
    assert registered_basis(TARGET) == {"analytical": "held-out", "airfoil": "in-sample"}


def test_a_wrong_reproduction_basis_is_a_fail_and_a_right_one_is_clean() -> None:
    wrong = "## Method\n\nThe baseline was reproduced on in-sample rows for Analytical and in-sample rows for Airfoil.\n"
    right = "## Method\n\nThe baseline was reproduced on held-out rows for Analytical and in-sample rows for Airfoil.\n"
    assert [f.severity for f in audit_basis(wrong, RESULTS, TARGET)[1]] == ["fail"]
    assert audit_basis(right, RESULTS, TARGET)[1] == []


def test_a_reproduction_with_no_stated_basis_is_a_warn_and_no_mention_is_not_checked() -> None:
    assert [f.severity for f in audit_basis("## Method\n\nThe baseline was reproduced within tolerance.\n", RESULTS, TARGET)[1]] == ["warn"]
    assert audit_basis("## Method\n\nSome other text.\n", RESULTS, TARGET)[1] == []


RECORDS = [
    {"title": "Isotonic recalibration of tree ensembles", "abstract": "We refit components by isotonic regression of tree ensembles.", "url": "u1"},
    {"title": "Graph neural networks for molecules", "abstract": "A message passing network for molecular property prediction.", "url": "u2"},
    {"title": "Deeper variable selection in trees", "abstract": "Choose the depth of variable selection in tree ensembles.", "url": "u3"},
]


def test_AUD_F_07_the_closest_prior_work_is_ranked_by_overlap_with_the_idea() -> None:
    top = closest("Refit each component by isotonic regression of the tree ensemble", RECORDS, k=2)
    assert top[0]["url"] == "u1" and all(r["url"] != "u2" for r in top)


def test_AUD_F_07_a_not_distinct_verdict_is_a_warn_naming_the_prior_work() -> None:
    ideas = {"C2: Isotonic refit": "Refit each component by isotonic regression of the tree ensemble."}
    claims, findings = audit_novelty(ideas, RECORDS, Judge(default=False))
    assert claims[0].kind == "novelty" and findings and findings[0].check == "novelty" and findings[0].severity == "warn"
    assert "Isotonic recalibration" in findings[0].summary
    _, none = audit_novelty(ideas, RECORDS, Judge(default=True))
    assert none == []


def test_one_targeted_search_adds_to_the_pool_and_a_failing_search_is_ignored() -> None:
    ideas = {"C3: Quantile trees": "Quantile smoothing of leaf values in tree ensembles."}
    extra = [{"title": "Quantile smoothing of leaf values", "abstract": "Quantile smoothing of leaf values in tree ensembles.", "url": "u4"}]
    _, findings = audit_novelty(ideas, RECORDS, Judge(default=False), search=lambda q: extra)
    assert any("Quantile smoothing" in f.summary for f in findings)

    def broken(query: str) -> list[dict]:
        raise RuntimeError("network")

    audit_novelty(ideas, RECORDS, Judge(default=True), search=broken)  # does not raise
