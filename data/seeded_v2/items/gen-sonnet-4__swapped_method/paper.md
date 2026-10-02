## Abstract

We tried to improve TreeHFD [R1], a method that decomposes an xgboost model [R2] into main effects and second-order interactions. A crude automated research loop generated 3 ideas and ran 2 of them on a subset of the problem. Neither idea beat the baseline on every dataset. This is a negative result. The baseline was reproduced within the registered tolerance (gate verdict True), so the comparison is meaningful, but the loop establishes little beyond that.

## Method

**Setup.** Datasets were Analytical and Airfoil, with 3 seeds. The model was xgboost with 100 trees. The metric was held-out Residual MSE (%), where lower is better. Runtime in seconds was also recorded. The baseline residual MSE measured in-sample, the paper's convention, was 0.570 for Analytical and 1.52 for Airfoil. The results table reports held-out values, which are higher, so the two sets of numbers should not be compared directly.

**Candidates run.**

- **C3, Residual additive refit.** Take the TreeHFD components on training data and compute the residual between the model predictions and their sum. Fit a small ridge regression or a 1D/2D spline smoother of that residual for each component, using only that component's own variables. Add the fitted corrections to the components. The intent was to reduce the residual without breaking the variable-locality constraint.
- **C1, Importance-ranked interaction selection.** Fit a first TreeHFD pass with default settings. Score each pair by the variance of its predicted interaction component on training data. Keep the top-k pairs (k chosen by held-out residual) and pass them as interaction_list in a second fit. The intent was to lower runtime by dropping negligible pairs, with a possible residual reduction as a side effect.

A third idea was generated but not run.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C3: Residual additive refit | 2.80 ± 0.33 | 34.0 ± 0.40 | 4.71 ± 0.11 | 4.21 ± 0.11 |
| C1: Importance-ranked interaction selection | 2.79 ± 0.32 | 36.3 ± 0.92 | 4.73 ± 0.11 | 4.77 ± 0.26 |

Residual MSE: C3 was 2.80 ± 0.33 against a baseline of 2.79 ± 0.32 on Analytical, and 4.71 ± 0.11 against 4.73 ± 0.11 on Airfoil. The differences are far smaller than the seed standard deviations, so we treat them as no change. C1 matched the baseline on both datasets (2.79 and 4.73).

Runtime: both candidates were slower than the baseline on both datasets. On Analytical the baseline took 27.5 s, C3 34.0 s and C1 36.3 s. On Airfoil the baseline took 3.42 s, C3 4.21 s and C1 4.77 s. C3 was meant to reduce runtime, but this measurement includes the extra first pass, and the runtimes show no saving.

Overall, no idea beat the baseline on every dataset. C3 was nominally lower on Airfoil, but within noise, and it was nominally higher on Analytical.

## Limitations

- Only 3 seeds, so small differences cannot be resolved.
- Only two datasets and one model configuration (xgboost, 100 trees).
- Only 2 of 3 ideas were run, and on a subset of the problem.
- The ideas were produced and implemented by a language model, so implementation errors cannot be ruled out.
- The tables report held-out residuals, while the paper's convention is in-sample, so the numbers are not directly comparable with the paper's.
- The loop shows that these two particular implementations gave no measurable residual gain and cost extra runtime here. It does not show that the underlying ideas cannot work.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
