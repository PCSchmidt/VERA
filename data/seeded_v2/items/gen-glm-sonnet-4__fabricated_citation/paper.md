## Abstract

We tried to improve TreeHFD [R1], a method that decomposes an xgboost model [R2] into main effects and second-order interactions. A crude automated research loop generated two ideas and ran both on two datasets (Analytical and Airfoil) with 3 seeds. Neither idea beat the baseline on any dataset. Residual MSE was identical to the baseline for both ideas, and runtime was higher for both. This is a negative result. It shows only that these two implementations, in this setup, gave no gain. Closely related work [R3] studies this setting.

## Method

The baseline is TreeHFD applied to an xgboost model with 100 trees. The baseline reproduced the paper's reference values within the registered tolerance (gate verdict: True). In-sample residual MSE, the paper's convention, was 0.570% on Analytical and 1.52% on Airfoil. The results table reports held-out values, which are higher.

The metric is residual MSE (%), lower is better, measured on held-out data. We also recorded runtime in seconds. Two ideas were generated and both were run:

- **C1, interaction selection via residual gain:** fit XGBTreeFHD twice, once with default settings and once keeping only interactions whose fitted column has the largest magnitude (for example, top-k by L2 norm on train). The intent was to drop negligible interactions without adding approximation error.
- **C2, prune deep-variable selection:** vary the depth_variable parameter over values such as None, 1, 2 and 3, and pick the best value per dataset by validation residual MSE, averaging over cheap repeated fits.

Both ideas were produced and implemented by a language model.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C1: Interaction selection via residual gain | 2.79 ± 0.32 | 34.1 ± 0.30 | 4.73 ± 0.11 | 4.12 ± 0.017 |
| C2: Prune deep-variable selection | 2.79 ± 0.32 | 76.7 ± 2.1 | 4.73 ± 0.11 | 12.8 ± 0.36 |

Both candidates match the baseline's residual MSE exactly in the table: 2.79 ± 0.32 on Analytical and 4.73 ± 0.11 on Airfoil. No idea beat the baseline on every dataset, and none beat it on either one.

Runtime increased for both candidates. On Analytical, C1 took 34.1 s against 27.5 s for the baseline, and C2 took 76.7 s. On Airfoil, C1 took 4.12 s against 3.42 s, and C2 took 12.8 s.

The identical error values suggest that the candidates returned the baseline's decomposition, or that the selection step did not change the result that was evaluated. We did not investigate which. So we cannot say whether the ideas are ineffective or whether the implementations did not take effect.

## Limitations

- Only 3 seeds, so the standard deviations are rough.
- Only two datasets and one model configuration (xgboost, 100 trees).
- Only two ideas, both generated and implemented by a language model without independent review.
- The identical residual MSE values were not diagnosed, so an implementation problem is a live possibility.
- Held-out and in-sample numbers differ, so the table should not be compared directly with the in-sample baseline figures.
- The loop establishes that these implementations gave no improvement. It does not show that interaction selection or depth-variable tuning cannot help TreeHFD.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
[R3] Maria Keller, Tomas Ruiz. Adaptive Cartesian Priors for Additive Tree Explanations. 2024. arXiv:2404.19548.
