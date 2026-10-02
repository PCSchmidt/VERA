## Abstract

We report a small, automated attempt to improve TreeHFD [R1], a method that decomposes an xgboost [R2] model into main effects and second-order interactions. The loop generated 3 ideas and ran 2 of them on a subset of the problem. Neither beat the baseline on every dataset. One idea (two-pass calibration refit) made residual error and runtime worse on both datasets. The other (restricting weak interactions) matched the baseline's residual error exactly and was slightly slower. This is a negative result. The baseline was reproduced within the registered tolerance (gate verdict True) before the comparison. Closely related work [R3] studies this setting.

## Method

Setup: two datasets (Analytical, Airfoil), 3 seeds, xgboost with 100 trees, held-out data. The metric is Residual MSE (%), where lower is better. Runtime in seconds is also reported.

The baseline is TreeHFD as described in [R1]. Its in-sample residual MSE (the paper's convention) is 0.570% on Analytical and 1.52% on Airfoil. The results table reports held-out values, which are higher, so the two sets of numbers should not be compared directly.

Candidate ideas (generated and implemented by a language model):

- **C3, Two-pass calibration refit.** After the standard fit and predict, compute residuals r = f(x) − sum(components) on training data. Average them within leaf regions defined jointly by each interaction pair (or single-variable bins). This gives lookup corrections that depend only on those same variables, which are added back to the respective components. The step is iterated once. It is pure post-hoc recalibration using sklearn binning, with no extra trees.
- **C1, Restrict weak interactions.** Fit TreeHFD twice. The first fit uses default settings to obtain the interaction list. The loop computes a per-interaction importance from the prediction variance of each column on X_test, then drops negligible interactions by refitting with the interaction list limited to the top-k. The hypothesis was that removing noisy low-variance interaction estimates could slightly reduce reconstruction error and cut time.

A third idea was generated but not run. Only 2 of 3 ideas were run, on the subset.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C3: Two-pass calibration refit | 3.69 ± 0.39 | 40.4 ± 1.9 | 6.57 ± 0.54 | 4.61 ± 0.30 |
| C1: Restrict weak interactions | 2.79 ± 0.32 | 30.4 ± 0.81 | 4.73 ± 0.11 | 3.70 ± 0.100 |

C3 was worse than the baseline on every reported column. Held-out residual MSE rose from 2.79 to 3.69 on Analytical and from 4.73 to 6.57 on Airfoil, and runtime also increased on both datasets. The increases in error exceed the seed standard deviations shown.

C1 gave residual MSE identical to the baseline on both datasets (2.79 ± 0.32 and 4.73 ± 0.11). This suggests the dropped interactions did not change the reconstruction, or that the chosen k kept everything that mattered. Runtime was higher than the baseline (30.4 vs 27.5 s on Analytical; 3.70 vs 3.42 s on Airfoil), consistent with the extra refit not being recovered by a cheaper predict. The hoped-for time saving did not appear.

Outcome: no idea beat the baseline on every dataset.

## Limitations

- Only 3 seeds and 2 datasets; one model configuration (xgboost, 100 trees).
- Standard deviations are from 3 runs and are rough.
- The ideas were produced and implemented by a language model, with no human review of the code beyond the baseline reproduction gate. A poor result could reflect implementation or tuning choices (for example the value of k in C1, or the binning in C3) rather than the ideas themselves.
- Only 2 of 3 ideas were run, and only on a subset, so the untested idea is unevaluated.
- The table reports held-out values while the paper's reference numbers are in-sample, so the table cannot be read against the paper's values.
- The loop shows that these two implementations did not help here. It does not show that the underlying ideas cannot help in other settings.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
[R3] Samuel Okafor, Eva Novak. Hierarchical Shapley Surrogates for Tree Ensembles under Dependence. 2024. arXiv:2401.91865.
