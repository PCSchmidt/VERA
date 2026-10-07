# ruff: noqa: E501
"""The second parent problem's kit: credal ambiguity sets on California Housing under a geographic shift (Increment 4).

Chen et al., "Bulk-Calibrated Credal Ambiguity Sets" (arXiv 2601.21324), Section 5.2, Tables 3 and 4. The harness
(`docker/sandbox-credal/harness.py`) runs the parent's own experiment for the baseline and an idea's `fit_predict` on the
parent's split for the ideas; the target (`docs/results/credal_baseline_target.json`) was registered from the paper
alone, before any baseline run. This module is text and small builders only; the gates and the audit are the loop's own.
"""

from __future__ import annotations

from pathlib import Path

from vera.loop import tables
from vera.loop.problem import REPO, ProblemKit
from vera.sandbox import SandboxLimits
from vera.schemas import Question, QuestionType

IMAGE = "vera-sandbox-credal:506c17f"
LABEL = "LV (baseline)"
METRICS = (
    ("mae", "MAE (1e4)"),
    ("rmse", "RMSE (1e4)"),
    ("p98_abs_error", "p98 absolute error (1e4)"),
    ("cvar_abs_error", "CVaR 2% absolute error (1e4)"),
    ("runtime_s", "Runtime (s)"),
)
REPRO = METRICS[:4]
EXAMPLE = '''import numpy as np
from sklearn.linear_model import QuantileRegressor


def fit_predict(X_train, y_train, X_test):
    """Least absolute deviations (ERM with the absolute loss): the median regression on standardised features."""
    mu, sd = X_train.mean(axis=0), X_train.std(axis=0) + 1e-12
    model = QuantileRegressor(quantile=0.5, alpha=0.0, solver="highs")
    model.fit((X_train - mu) / sd, y_train)
    return model.predict((X_test - mu) / sd)'''

PROBLEM_TEXT = (
    "The task is linear regression for the housing value on California Housing (8 features) under a geographic "
    "deployment shift: a model is trained on the Eastern 50% of the districts and judged on the Western 20% (the "
    "30% band between them is left out). The parent's method, LV (Chen et al., arXiv 2601.21324), fits a linear "
    "predictor with the absolute loss against a bulk-calibrated credal ambiguity set; the paper compares it with CVaR, "
    "Wasserstein, ridge and ERM baselines. Quality is the test error, in units of 1e4 dollars: MAE (the metric ideas "
    "are compared on), RMSE, the 98th percentile of the absolute error and its 2% tail CVaR (all lower is better)."
)


def baseline_example() -> str:
    return EXAMPLE


def ideate_prompt(deps, baseline_table: str, n: int) -> str:
    from vera.loop import literature_context

    return (
        PROBLEM_TEXT + "\n\n"
        f"Baseline results (LV, the parent's method, reproduced):\n\n{baseline_table}\n\n"
        f"Propose {n} distinct, concrete ideas that could lower the test MAE under this shift, each a model of the housing "
        "value from the training rows' features and values (no test labels), buildable in a few minutes on a CPU with "
        "numpy, scipy and scikit-learn (for example: a different robust or tail-aware loss, reweighting training rows "
        "toward the test region's covariates, feature transformations, shrinking toward a robust fit, combining fits). "
        'Reply with a JSON array of objects {"name": "<2-5 words>", "description": "<about 50 words: exactly what is '
        'computed>"} and nothing else.'
        + (literature_context.for_ideas(deps.extra["literature"]) if deps.extra.get("literature") else "")
    )


def implement_prompt(idea: dict, error: str | None, previous: str | None) -> str:
    prompt = (
        "Implement this idea as a Python module defining\n\n"
        "    def fit_predict(X_train, y_train, X_test):\n"
        "        ... return y_pred\n\n"
        "`X_train` (n x 8) and `X_test` (m x 8) are float numpy arrays of the California Housing features and `y_train` "
        "the housing values in dollars; return a numpy array of m predicted values. The harness computes the error "
        "metrics itself on the held-out Western districts and never shows `fit_predict` the test labels. It also calls "
        "`fit_predict` a second time with the training rows in another order and rejects the run if the predictions "
        "change, so do not depend on row order or on random state you do not seed. You may import numpy, scipy, sklearn "
        "and cvxpy. There is no network. This is a simple baseline, as the interface example:\n\n```python\n"
        + EXAMPLE + "\n```\n\n"
        f"Idea: {idea['name']}\n{idea['description']}\n"
    )
    if error:
        prompt += f"\nYour previous attempt failed: {error}\n\nPrevious code:\n```python\n{previous}\n```\nFix it.\n"
    return prompt


def idea_worth_run(name: str, description: str, baseline_table: str) -> tuple[Question, str]:
    question = Question(
        id="loop.idea_worth_run",
        type=QuestionType.SCORE,
        text=(
            f'Is the idea "{name}" worth a subset run? Score 1 if it is unlikely to lower the test MAE or cannot be built '
            "from numpy, scipy and scikit-learn within a few minutes of CPU; 3 if it is plausible but unremarkable; 5 if it "
            "is likely to lower the test MAE under the East-to-West shift and is clearly implementable."
        ),
        scale=(1, 5),
    )
    material = (
        "A research loop is trying to improve on LV, the parent's robust linear-regression method, for California Housing "
        "under a geographic shift: the aim is a lower test MAE on the Western districts, for a model trained on the "
        "Eastern ones (no test labels may be used). A candidate is a function from training rows and test features to "
        f"predicted values.\n\nBaseline results:\n\n{baseline_table}\n\nCandidate idea: {name}\n{description}"
    )
    return question, material


def baseline_reproduced(target: dict, results: dict[str, dict], n_seeds: int, datasets: list[str] | None = None):
    """(question, material, shadow): do the reproduced LV means match the paper's Table 3 within the registered relative
    tolerance on all four metrics, and does LV have the lowest mean of the five methods on each (the paper's claim)?"""
    datasets = datasets or ["california_housing"]
    tol = target["tolerance"]["relative"]
    ref = target["reference"]["lv"]
    cell = results[tables.BASELINE]["california_housing"]
    means = tables.rendered_means(results, datasets, REPRO)
    others = cell.get("reference_methods") or {}
    rows = ["| Method | " + " | ".join(name for _, name in REPRO) + " |", "|" + "---|" * (len(REPRO) + 1)]
    for label, c in [("LV (this run)", cell), *[(k, v) for k, v in others.items()]]:
        rows.append(f"| {label} | " + " | ".join(
            tables.fmt_sig(c[k]["mean"]) if c.get("valid") and c.get(k) else "n/a" for k, _ in REPRO) + " |")  # fmt: skip
    material = (
        "Baseline reproduction check for the credal-ambiguity-sets problem (California Housing, East to West).\n"
        "Reference values from the paper's Table 3 for LV (units of 1e4): "
        + "; ".join(f"{name} {ref[k][0]}" for k, name in REPRO)
        + f".\nTolerance: {tol:.0%}, relative to the reference value.\n\n" + "\n".join(rows)
    )
    question = Question(
        id="loop.baseline_reproduced",
        type=QuestionType.BOOLEAN,
        text=(
            "Do this run's LV means match the reference values within the stated relative tolerance on all four metrics, "
            "and does LV have the lowest value of the five methods on each metric? A metric matches only if the absolute "
            "difference between this run's LV mean and the reference, divided by the reference, is at most the tolerance."
        ),
    )
    within = all(
        abs(means[(tables.BASELINE, "california_housing", k)] - ref[k][0]) <= tol * ref[k][0] + 1e-9 for k, _ in REPRO
    )
    best = bool(others) and all(
        cell[k]["mean"] <= min(v[k]["mean"] for v in others.values() if v.get("valid") and v.get(k))
        for k, _ in REPRO
    )
    return question, material, bool(within and best)


def facts(state: dict, deps) -> str:
    results = state["results"]
    ideas = {i["name"]: i["description"] for i in state["ideas"]}
    ran = [m for m in results if m != tables.BASELINE and " without " not in m]  # ablation rows are not ideas
    best = state.get("best")
    lines = [
        "- Baseline reproduced against the parent paper's Table 3 (LV row) within the registered 5% tolerance, with LV "
        f"best of the five methods: yes (gate verdict {state['verdicts']['baseline']['answer']}).",
        f"- Data: California Housing, trained on the Eastern 50%, tested on the Western 20% (30% gap); {deps.n_seeds} "
        "replications; error metrics in units of 1e4 dollars, lower is better; the parent's solver MOSEK was replaced by "
        "the open solver Clarabel.",
        f"- Ideas generated: {len(state['ideas'])}; run on the subset: {len(ran)}.",
        "- Outcome: " + (f'"{best}" beat LV on MAE.' if best else "no idea beat LV on MAE."),
    ]
    lines += [f"- {m}: {ideas.get(m, '')}" for m in ran]
    return "\n".join(lines)


WRITEUP_INTRO = (
    "Write a short research report on an attempt to improve LV, a bulk-calibrated credal-ambiguity-set method for "
    "robust linear regression, on California Housing under an East-to-West geographic shift. "
)
WRITEUP_LIMITS = "(few replications, one dataset, one split, a substituted solver, ideas produced and implemented by a language model)"

HARNESS_DIR = REPO / "docker" / "sandbox-credal"
CREDAL = ProblemKit(
    id="credal",
    method_name="LV",
    baseline_label=LABEL,
    function_name="fit_predict",
    harness_dir=Path(HARNESS_DIR),
    metrics=METRICS,
    primary="mae",
    image=IMAGE,
    baseline_limits=SandboxLimits(wall_seconds=7200, memory_mb=8192, cpus=8.0, pids=1024, max_workdir_mb=1024),
    experiment_limits=SandboxLimits(wall_seconds=1800, memory_mb=4096, cpus=4.0, pids=512),
    repro_metrics=REPRO,
    repro_metric="mae",
    ideate_system=(
        "You are a machine-learning researcher improving a robust regression method under distribution shift. Reply "
        "only with what is asked, in the requested format."
    ),
    ideate_prompt=ideate_prompt,
    implement_prompt=implement_prompt,
    idea_worth_run=idea_worth_run,
    baseline_reproduced=baseline_reproduced,
    baseline_example=baseline_example,
    writeup_intro=WRITEUP_INTRO,
    writeup_limits=WRITEUP_LIMITS,
    extra={"facts": facts},
)
