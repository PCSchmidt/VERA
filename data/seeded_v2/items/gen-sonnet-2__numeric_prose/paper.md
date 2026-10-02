## Abstract

We tried to improve TreeHFD [R1], a method that decomposes an xgboost model [R2] into main effects and second-order interactions. A crude automated research loop generated 3 ideas and ran 2 of them on a subset of the problem: C3 (residual backfitting of components) and C2 (co-occurrence pair selection). The baseline reproduced the paper's reference values within the registered tolerance (gate verdict True). **No idea beat the baseline on every dataset.** C3 was slightly worse than the baseline on both datasets and slower. C2 was slightly better on Analytical, within the noise, and much worse on Airfoil. This is a negative result.

## Method

Setup: two datasets (Analytical, Airfoil), 3 seeds, xgboost with 100 trees, evaluated on held-out data. The metric is residual MSE (%), where lower is better. Runtime in seconds is also reported. The baseline residual MSE in-sample, which is the paper's convention, is 0.570 (Analytical) and 1.52 (Airfoil). The results table reports held-out values, which are higher, so the table should not be compared directly with the paper's in-sample numbers.

Ideas tested:

- **C3, residual backfitting of components.** After fitting TreeHFD, compute training residuals r = f(X) − sum of components. Fit a one-dimensional smoother (e.g. isotonic or binned means) of r on each variable, and a 2D binned smoother for each listed pair, in a few backfitting passes. Add the results to the corresponding components. Each component stays a function of its own variables only. The hope was that the held-out residual would shrink.
- **C2, co-occurrence pair selection.** Parse the xgboost trees and count, weighted by split gain or cover, how often each variable pair appears together on the same root-to-leaf path. Pass the top-weighted pairs as interaction_list. The hope was that pairs the model actually uses are covered, so residual from missing interactions drops, and unused pairs are skipped to save time.

The third generated idea was not run.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C3: Residual backfitting of components | 2.83 ± 0.33 | 33.8 ± 1.3 | 4.79 ± 0.18 | 4.56 ± 0.14 |
| C2: Co-occurrence pair selection | 2.69 ± 0.30 | 33.4 ± 0.099 | 9.12 ± 0.91 | 4.10 ± 0.080 |

C3 did not reduce held-out residual. On Analytical it gave 2.83 ± 0.33 against 2.79 ± 0.32 for the baseline, and on Airfoil 4.79 ± 0.18 against 4.73 ± 0.11. Both differences are well inside the seed spread, so C3 is at best equal to the baseline, and it cost more time (33.8 s vs 27.5 s on Analytical, 4.56 s vs 3.43 s on Airfoil).

C2 gave 2.69 ± 0.30 on Analytical, a small improvement relative to the spread, which we do not treat as established with 3 seeds. On Airfoil it gave 9.12 ± 0.91 against 4.73 ± 0.11, clearly worse. The pair-selection rule apparently dropped interactions that mattered there; we did not investigate why. C2 was also slower on both datasets (33.4 s vs 27.5 s, and 4.10 s vs 3.42 s), so the hoped-for time saving did not appear. The extra runtime may include the cost of parsing trees or smoothing, but we did not profile it.

Overall, no idea beat the baseline on every dataset.

## Limitations

- Only 3 seeds, so small differences (the C3 gaps and the C2 gain on Analytical) cannot be distinguished from noise.
- Only two datasets and one model configuration (xgboost, 100 trees).
- Only 2 of 3 generated ideas were run, and on a subset of the problem.
- The ideas were produced and implemented by a language model, so implementation bugs or weak tuning could explain poor results; we did not check this. The negative results therefore say these specific implementations did not help, not that the underlying ideas cannot work.
- Held-out and in-sample residuals differ, so the table is not comparable to the paper's in-sample numbers.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
