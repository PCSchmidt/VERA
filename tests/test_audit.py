"""AUD-F-03, AUD-F-04, AUD-F-09, RSH-F-05: the minimal P1 audit of the loop's write-up.

Offline, with a stub lookup and a judge that answers as a correct judge would."""

from __future__ import annotations

import re

import pytest

from tests.loop_fakes import BASELINE_OK, IDEA_RESULTS, REFS, TARGET, ds, paper
from vera.audit import SKIPPED, AuditRun, overall_of, render_markdown, run_audit
from vera.audit.bibliography import LookupUnavailable, normalise
from vera.audit.numbers import matches, numbers_in, sentences
from vera.loop import tables
from vera.loop.stages import LoopDeps
from vera.loop.writeup import assemble
from vera.schemas import Question, Verdict

RESULTS = {tables.BASELINE: BASELINE_OK, "C1: shared knots": IDEA_RESULTS["C1"], "C2: ridge leaves": IDEA_RESULTS["C2"]}
RESULTS_JSON = {
    "run_id": "t",
    "metric": "residual_mse_pct",
    "n_seeds": 3,
    "datasets": ["analytical", "airfoil"],
    "results": RESULTS,
    "best": "C1: shared knots",
    "ideas": [{"name": "C1: shared knots"}, {"name": "C2: ridge leaves"}],
}


def clean_text(extra: str = "") -> str:
    """A compliant draft with VERA's own table and reference list, as the write-up stage produces."""
    deps = LoopDeps(
        spec=None,
        target={},
        generator=None,
        judge=None,
        sandbox=None,
        budget=None,  # type: ignore[arg-type]
        run_dir=None,
        data_dir=None,
    )
    draft = paper(extra=extra)
    return assemble(draft, {"results": RESULTS}, _with_datasets(deps), REFS)


def _with_datasets(deps: LoopDeps) -> LoopDeps:
    from tests.loop_fakes import make_spec  # noqa: PLC0415

    deps.spec = make_spec()
    return deps


class CorrectJudge:
    """Answers `cite.contains_entry` by comparing normalised titles, and `num.claim_consistent` by checking that every
    number in the claim appears in the table as written. `overrides` forces an answer; `confidence` sets certainty."""

    def __init__(self, overrides: dict | None = None, confidence: float = 0.95) -> None:
        self.overrides, self.confidence, self.asked = overrides or {}, confidence, []

    def __call__(self, q: Question, material: str) -> tuple[Verdict, bool]:
        self.asked.append(q.id)
        if q.id in self.overrides:
            answer = self.overrides[q.id]
        elif q.id == "cite.contains_entry":
            title = re.search(r'titled "(.*)"\?', q.text).group(1)
            answer = any(normalise(title) in normalise(ln) for ln in material.splitlines() if ln.startswith("["))
        else:
            claim = q.text.split("Claim: ", 1)[1]
            answer = all(x in material for x in numbers_in(claim))
        v = Verdict(
            question_id=q.id,
            answer=answer,
            confidence=self.confidence,
            confidence_source="self_report",
            backend="fake",
            escalated=False,
            cost_usd=0.0002,
            latency_ms=1,
            trace_id="t",
            producer_id="p3.write_up",
            judge_id="p2.judge",
        )
        return v, self.confidence >= 0.7


def audit(text: str, judge: CorrectJudge | None = None, lookup=None) -> AuditRun:
    return run_audit(
        text,
        RESULTS_JSON,
        REFS,
        ask=judge or CorrectJudge(),
        lookup=lookup or (lambda t: []),
        paper_id="t",
        paper_source="paper.md",
        target=TARGET,
    )


def severities(run: AuditRun) -> list[str]:
    return [f.severity for f in run.report.findings]


# ── a clean write-up ─────────────────────────────────────────────────────────────────────────────────


def test_AUD_F_03_a_clean_write_up_is_green_and_needs_no_lookup() -> None:
    calls = []
    run = audit(clean_text(), lookup=lambda t: calls.append(t) or [])
    assert run.report.overall == "green" and run.report.findings == []
    assert calls == []  # every reference was accounted for by the retrieval log
    assert run.report.checks_run == ["citation", "numeric"] and set(run.report.checks_skipped) == set(SKIPPED)
    assert {c.kind for c in run.claims} == {"citation", "numeric"}


# ── citations ────────────────────────────────────────────────────────────────────────────────────────


def test_AUD_F_03_an_altered_reference_is_a_fail_with_the_logged_record_as_evidence() -> None:
    text = clean_text().replace("XGBoost: A Scalable Tree Boosting System", "XGBoost: A Scalable Tree Learning System")
    run = audit(text)
    (f,) = run.report.findings
    assert f.severity == "fail" and f.check == "citation" and "differs from the record" in f.summary
    assert f.evidence[0].source == "log" and f.evidence[0].matched is False and "R2" in f.evidence[0].reference


FAKE = (
    "[R3] Maria Keller, Tomas Ruiz. Adaptive Cartesian Priors for Additive Tree Explanations. 2024. arXiv:2403.99999."
)


def fabricated(extra_cite: bool = True) -> str:
    text = clean_text().replace(
        "## Limitations", "Related work [R3] is relevant.\n\n## Limitations" if extra_cite else "## Limitations"
    )
    return text.rstrip() + "\n" + FAKE + "\n"


def test_AUD_F_03_a_fabricated_reference_with_no_candidates_is_a_fail() -> None:
    run = audit(fabricated(), lookup=lambda t: [])
    (f,) = run.report.findings
    assert f.severity == "fail" and "no bibliographic source returned" in f.summary
    assert f.evidence[0].source == "bibliography_api" and f.evidence[0].matched is False
    assert run.report.overall == "red"


def test_AUD_F_03_a_near_miss_candidate_is_put_to_the_judge_and_rejected() -> None:
    near = [
        {
            "title": "Adaptive Cartesian Priors for Additive Forest Explanations",
            "authors": ["A. Other"],
            "year": "2024",
            "id": "arXiv:2401.00001",
            "url": "https://arxiv.org/abs/2401.00001",
            "source": "arxiv",
        }
    ]
    judge = CorrectJudge()
    run = audit(fabricated(), judge, lookup=lambda t: near)
    (f,) = run.report.findings
    assert judge.asked == ["cite.contains_entry"] and f.severity == "fail" and f.verdicts[0].answer is False
    assert f.evidence[0].reference == "https://arxiv.org/abs/2401.00001"  # the closest record is the evidence


def test_AUD_F_03_a_real_paper_outside_the_log_is_verified_through_the_sources() -> None:
    exact = [
        {
            "title": "Adaptive Cartesian Priors for Additive Tree Explanations",
            "authors": ["M. Keller"],
            "year": "2024",
            "id": "arXiv:2403.99999",
            "url": "https://arxiv.org/abs/2403.99999",
            "source": "arxiv",
        }
    ]
    run = audit(fabricated(), lookup=lambda t: exact)
    assert run.report.findings == [] and run.report.overall == "green"


def test_AUD_F_03_an_exact_title_with_a_different_year_is_info_not_a_miss() -> None:
    journal = [
        {
            "title": "Adaptive Cartesian Priors for Additive Tree Explanations",
            "authors": [],
            "year": "2026",
            "id": "10.1/x",
            "url": "https://doi.org/10.1/x",
            "source": "crossref",
        }
    ]
    run = audit(fabricated(), lookup=lambda t: journal)
    (f,) = run.report.findings
    assert f.severity == "info" and "different year" in f.summary and run.report.overall == "green"


@pytest.mark.parametrize("make", ["unsure", "unavailable"])
def test_AUD_F_03_what_cannot_be_checked_is_a_warn_not_a_fail(make: str) -> None:
    near = [{"title": "Something Related", "authors": [], "year": "2024", "id": "x", "url": "", "source": "arxiv"}]
    if make == "unsure":
        run = audit(fabricated(), CorrectJudge(confidence=0.5), lookup=lambda t: near)
    else:

        def down(t: str):
            raise LookupUnavailable("crossref: ConnectError; arxiv: ConnectError")

        run = audit(fabricated(), lookup=down)
    (f,) = run.report.findings
    assert f.severity == "warn" and run.report.overall == "amber"
    assert f.evidence and f.evidence[0].matched is None


def test_AUD_F_03_an_in_text_citation_with_no_record_is_a_fail() -> None:
    run = audit(clean_text().replace("on xgboost models [R2]", "on xgboost models [R2] and [R9]", 1))
    (f,) = run.report.findings
    assert f.severity == "fail" and "[R9]" in f.summary and f.claim_ids == ["cite:R9"]


# ── numbers ──────────────────────────────────────────────────────────────────────────────────────────


def test_AUD_F_04_a_table_cell_that_differs_from_results_is_a_fail_with_its_source() -> None:
    text = clean_text().replace("2.40 ± 0.10", "2.97 ± 0.10", 1)
    run = audit(text)
    (f,) = run.report.findings
    assert f.severity == "fail" and f.check == "numeric" and "2.97" in f.summary
    assert "results.json:TreeHFD (baseline)/analytical/residual_mse_pct" in f.evidence[0].reference


def test_AUD_F_04_a_table_row_for_an_unknown_method_is_a_fail() -> None:
    text = clean_text().replace("C1: shared knots |", "C9: invented |", 1)
    assert "fail" in severities(audit(text))


def test_AUD_F_04_prose_numbers_must_exist_in_results_as_rounded_and_derived_values_are_allowed() -> None:
    ok = clean_text(
        "\nThe baseline residual was 2.4% held-out on Analytical, and C1 lowered it by 0.6 points, or 25% (to 1.8).\n"
    )
    # the deterministic layer accepts rounded and derived numbers; the judge (forced to agree here) is tested elsewhere
    run = audit(ok, CorrectJudge(overrides={"num.claim_consistent": True}))
    assert run.report.findings == [], [f.summary for f in run.report.findings]


def test_AUD_F_04_an_invented_number_in_a_results_claim_is_a_fail_and_elsewhere_a_warn() -> None:
    run = audit(clean_text("\nC1 lowered the baseline residual by 41% on Analytical.\n"))
    (f,) = run.report.findings
    assert f.severity == "fail" and "41" in f.summary and f.evidence[0].reference == "results.json"
    run2 = audit(clean_text("\nThe study was funded by grant 5873.4 of an agency.\n"))
    (g,) = run2.report.findings
    assert g.severity == "warn"  # not a results claim: unverifiable, not necessarily wrong


def test_AUD_F_04_a_real_number_on_the_wrong_method_is_now_a_fail_not_amber() -> None:
    claim = "\nThe baseline residual was 1.80 held-out on Analytical.\n"  # 1.80 is C1's value, not the baseline's
    run = audit(clean_text(claim), CorrectJudge())
    (f,) = run.report.findings
    assert f.severity == "fail" and "wrong method or dataset" in f.summary and "C1" in f.summary
    assert f.verdicts == [] and run.report.overall == "red"  # deterministic: the judge was not needed


def test_AUD_F_04_a_sentence_naming_no_cell_is_still_the_judges_to_catch() -> None:
    claim = "\nThe held-out residual of 1.80 shows a clear gain.\n"  # names no method and no dataset: nothing to align
    run = audit(clean_text(claim), CorrectJudge(overrides={"num.claim_consistent": False}))
    (f,) = run.report.findings
    assert f.severity == "warn" and "could not confirm the claim" in f.summary and f.verdicts[0].answer is False
    assert severities(audit(clean_text(claim), CorrectJudge(confidence=0.5))) == ["warn"]
    assert audit(clean_text(claim), CorrectJudge(overrides={"num.claim_consistent": True})).report.findings == []


@pytest.mark.parametrize(
    "claim",
    [
        "\nC1 reached 1.80 on Analytical against the baseline's 2.4.\n",  # its own cell, and the baseline's
        "\nThe baseline residual was 2.4 held-out on Analytical.\n",
        "\nOn both datasets C1 improved on the baseline (1.80 and 2.20 against 2.4 and 4.7).\n",
        "\nC1 cut the Analytical residual by 0.6 points, from 2.4 to 1.80.\n",
    ],
)
def test_AUD_F_04_numbers_on_the_named_methods_and_datasets_are_not_flagged(claim: str) -> None:
    run = audit(clean_text(claim), CorrectJudge())
    assert [f for f in run.report.findings if "wrong method" in f.summary] == []


def test_AUD_F_04_a_sentence_that_names_no_idea_is_about_the_one_under_discussion() -> None:
    text = (
        "\nC1 improved on the baseline.\n"
        "Its held-out Residual MSE was 1.80 on Analytical, versus 2.4 for TreeHFD.\n"  # "Its" is C1: correct
    )
    assert [f for f in audit(clean_text(text), CorrectJudge()).report.findings if "wrong method" in f.summary] == []
    other = "\nC2 improved on the baseline.\nIts held-out Residual MSE was 2.20 on Analytical, versus 2.4 for TreeHFD.\n"  # noqa: E501
    # the same sentence after a different idea: 2.20 is C1's Airfoil value, so it is not C2's and not Analytical's
    (f,) = [f for f in audit(clean_text(other), CorrectJudge()).report.findings if f.severity == "fail"]
    assert "wrong method or dataset" in f.summary


def test_AUD_F_04_a_number_with_fewer_than_three_significant_digits_is_not_checked_for_placement() -> None:
    claim = "\nC1 reached a residual of 2.2 on Analytical.\n"  # 2.2 happens to be C1's Airfoil value at this precision
    findings = audit(clean_text(claim), CorrectJudge()).report.findings
    assert [f for f in findings if "wrong method" in f.summary] == []


def test_AUD_F_04_a_value_of_another_dataset_is_flagged() -> None:
    claim = "\nC1 reached a residual of 2.20 on Analytical.\n"  # 2.20 is C1's Airfoil value
    (f,) = audit(clean_text(claim), CorrectJudge()).report.findings
    assert f.severity == "fail" and "C1: shared knots / airfoil" in f.summary


def test_AUD_F_04_what_is_not_a_result_is_not_extracted() -> None:
    text = (
        "## Method\n\nSee Benard (2025), [R1], arXiv:2510.24815 and Table 1. We used 3 seeds and C2: 4 ideas. "
        "Section 2 explains it.\n\n## References\n\n[R1] x. y. 2025. arXiv:2510.24815."
    )
    assert [n for _, s in sentences(text) for n in numbers_in(s)] == []


@pytest.mark.parametrize(
    ("x", "ok"),
    [("2.79", True), ("2.8", True), ("2.7", False), ("2.97", False), ("3", True), ("2.792", True), ("2.795", False)],
)
def test_AUD_F_04_a_number_matches_a_known_value_to_the_precision_it_is_written_in(x: str, ok: bool) -> None:
    assert matches(x, {2.7923}) is ok


# ── the report ───────────────────────────────────────────────────────────────────────────────────────


def test_AUD_F_09_every_finding_links_to_its_evidence() -> None:
    text = clean_text("\nC1 lowered the baseline residual by 41% on Analytical.\n").replace(
        "2.40 ± 0.10", "2.97 ± 0.10", 1
    )
    text = text.replace("on xgboost models [R2]", "on xgboost models [R2] [R9]", 1) + FAKE + "\n"
    run = audit(text)
    assert len(run.report.findings) >= 4 and {f.check for f in run.report.findings} == {"citation", "numeric"}
    for f in run.report.findings:
        assert f.evidence and all(e.reference and e.claim_id in f.claim_ids for e in f.evidence)
    assert "evidence:" in render_markdown(run) and run.report.overall == "red"


def test_RSH_F_05_overall_follows_the_worst_finding_and_cost_follows_the_judge() -> None:
    assert overall_of([]) == "green"
    run = audit(
        fabricated(),
        CorrectJudge(),
        lookup=lambda t: [{"title": "Other", "authors": [], "year": "2024", "id": "x", "url": "", "source": "arxiv"}],
    )
    assert run.report.overall == "red" and run.report.total_cost_usd == pytest.approx(0.0002)


def test_the_audit_does_not_modify_the_results_it_audits() -> None:
    import copy  # noqa: PLC0415

    before = copy.deepcopy(RESULTS_JSON)
    audit(clean_text())
    assert RESULTS_JSON == before and ds(1.0)["valid"]


def test_AUD_F_04_a_sentence_about_configuration_is_not_put_to_the_judge() -> None:
    """The first live dev run failed unmodified papers because the judge, asked whether 'xgboost with 100 trees,
    reproduced against the paper's reference' was consistent with the table, rightly said the table does not show it."""
    judge = CorrectJudge(overrides={"num.claim_consistent": False})  # would fail anything it were asked about
    text = clean_text(
        "\nThe baseline was reproduced against the paper's reference value of 2.0 using xgboost with 100 trees "
        "over 3 seeds.\n"
    )
    run = audit(text, judge)
    assert run.report.findings == [] and "num.claim_consistent" not in judge.asked
    # but a sentence that also states a table value is still checked
    mixed = clean_text("\nWith 100 trees the baseline residual was 2.40 held-out on Analytical.\n")
    audit(mixed, judge)
    assert judge.asked == ["num.claim_consistent"]


def test_AUD_F_04_a_design_number_in_the_method_section_is_a_warn_not_a_fail() -> None:
    """Found in the generator comparison: 'top-k covering 95% cumulative gain', a threshold the method uses, was failed
    as an unsupported result because of the bare percent sign."""
    text = clean_text().replace(
        "## Method\n\n",
        "## Method\n\nKeep only pairs above a threshold, for example the top-k covering 95% cumulative gain. "
        "Depth 4 reduced the residual in a preliminary design pass.\n\n",
        1,
    )
    run = audit(text)
    assert [f.severity for f in run.report.findings] == ["warn"] and run.report.overall == "amber"
    # the same words in the Results section, with a figure that is not in results, are still a fail
    text2 = clean_text().replace("## Results\n\n", "## Results\n\nDepth 4 reduced the residual by 95%.\n\n", 1)
    assert audit(text2).report.overall == "red"
    # and a bare percent with no result vocabulary is not a results claim anywhere
    text3 = clean_text().replace("## Results\n\n", "## Results\n\nThe grid kept 95% of pairs.\n\n", 1)
    assert [f.severity for f in audit(text3).report.findings] == ["warn"]
