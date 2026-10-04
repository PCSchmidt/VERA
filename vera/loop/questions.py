"""The loop's judge questions: their wording, the material the judge reads, and the programmatic shadow answer.

`beats_baseline` and `best_method` use the Increment 1 benchmark's wording and table layout (vera/bench/build.py), so
the judge is asked what it was measured on. Each builder returns the `Question` and, where the answer can be
computed from the run's own table, a shadow answer: recorded beside the verdict, never used as the gate, and the
label for the Increment 2 re-test on real gate decisions.
"""

from __future__ import annotations

from vera.loop import problem, tables
from vera.schemas import Question, QuestionType


def baseline_reproduced(
    target: dict, results: dict[str, dict], n_seeds: int, datasets: list[str] | None = None
) -> tuple[Question, str, bool]:
    """(question, material, shadow answer): does the baseline match the paper within tolerance on every dataset?

    `datasets` are the datasets this run uses (default: all in the registered target); the registered references
    and tolerance are unchanged, a run is checked on the datasets it runs that have a registered reference. The
    target's `extension_datasets` have none: the gate node only requires their baseline result to be valid."""
    if problem.active().baseline_reproduced:
        return problem.active().baseline_reproduced(target, results, n_seeds, datasets)
    datasets = [d for d in (datasets or target["datasets"]) if d in target["datasets"]]  # not the extensions
    tol = target["tolerance"]["absolute_pct_points"]
    means = tables.rendered_means(results, datasets, tables.REPRO_METRICS)
    shown = tables.valid_datasets(results, datasets)
    names = dict(tables.REPRO_METRICS)
    basis = {d: target["datasets"][d]["reproduction_metric"] for d in datasets}  # registered per dataset
    refs = "; ".join(
        f"{tables.dataset_label(d)} {target['datasets'][d]['reference_pct']:.1f} "
        f"(compare the {'in-sample' if basis[d] == tables.REPRO_METRIC else 'held-out'} column)"
        for d in datasets
    )
    material = (
        "Baseline reproduction check for the TreeHFD problem.\n"
        f"Reference values from the TreeHFD paper, Residual MSE (%): {refs}.\n"
        f"Tolerance: {tol:.1f} percentage points, absolute.\n\n"
        + tables.render_results({tables.BASELINE: results[tables.BASELINE]}, datasets, n_seeds, tables.REPRO_METRICS)
    )
    question = Question(
        id="loop.baseline_reproduced",
        type=QuestionType.BOOLEAN,
        text=(
            "Do the reproduced Residual MSE values match the reference values within the stated tolerance on every "
            "dataset? Each reference names the column to compare (in-sample or held-out). A dataset matches only if "
            "the absolute difference between its mean in that column and its reference is at most the tolerance; a "
            "dataset missing from the results table does not match. Ignore the other column and the ± spread."
        ),
    )
    shadow = set(shown) == set(datasets) and all(
        abs(means[(tables.BASELINE, d, basis[d])] - target["datasets"][d]["reference_pct"]) <= tol + 1e-9
        for d in datasets
    )
    assert set(basis.values()) <= set(names), "target names an unknown reproduction metric"
    return question, material, shadow


def idea_worth_run(name: str, description: str, baseline_table: str) -> tuple[Question, str]:
    if problem.active().idea_worth_run:
        return problem.active().idea_worth_run(name, description, baseline_table)
    question = Question(
        id="loop.idea_worth_run",
        type=QuestionType.SCORE,
        text=(
            f'Is the idea "{name}" worth a subset run? Score 1 if it is unlikely to lower the Residual MSE or cannot '
            "be built from an xgboost model and TreeHFD's public API within a few minutes of CPU; 3 if it is "
            "plausible but unremarkable; 5 if it is likely to lower the Residual MSE and is clearly implementable."
        ),
        scale=(1, 5),
    )
    material = (
        "A research loop is trying to improve on the TreeHFD baseline for decomposing xgboost models: the aim is a "
        "lower Residual MSE (the squared gap between the xgboost model's predictions and the sum of the "
        "decomposition's components, relative to the variance of the model's predictions). A candidate must return "
        "an intercept and components that each depend only on their own one or two variables.\n\n"
        f"Baseline results:\n\n{baseline_table}\n\nCandidate idea: {name}\n{description}"
    )
    return question, material


def beats_baseline(method: str, dataset: str, results: dict[str, dict], datasets: list[str], n_seeds: int):
    """(question, material, shadow answer) for one candidate on one dataset's primary metric."""
    means = tables.rendered_means(results, datasets)
    question = Question(
        id="loop.beats_baseline",
        type=QuestionType.BOOLEAN,
        text=(
            f'Does "{method}" beat the {tables.PROBLEM_NAME} baseline on {tables.METRIC_NAME[tables.PRIMARY]} for the '
            f"{tables.dataset_label(dataset)} dataset? It beats it only if its mean is strictly better (lower "
            "is better for this metric); ignore the ± spread."
        ),
    )
    return question, tables.render_results(results, datasets, n_seeds), tables.beats(means, method, dataset)


def best_method(dataset: str, results: dict[str, dict], datasets: list[str], n_seeds: int):
    """(question, material, shadow answer or None if the best is tied) for one dataset's primary metric."""
    means = tables.rendered_means(results, datasets)
    methods = list(results)
    question = Question(
        id="loop.best_method",
        type=QuestionType.CHOICE,
        text=(
            f"Which method has the best mean {tables.METRIC_NAME[tables.PRIMARY]} on the "
            f"{tables.dataset_label(dataset)} dataset? Ignore the ± spread."
        ),
        options=methods,
    )
    return question, tables.render_results(results, datasets, n_seeds), tables.best(means, methods, dataset)
