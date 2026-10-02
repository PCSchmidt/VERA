## Abstract

TreeHFD decomposes a trained xgboost model into main effects and second-order interactions [R1], [R2]. We ran a small, crude improvement loop: reproduce the published baseline on an analytical dataset, generate three candidate ideas with a language model, and implement and test two of them. Neither implemented idea beat the baseline on the dataset tested. This report states the negative result plainly and lists what the loop did and did not establish. Closely related work [R3] studies this setting.

## Method

**Setup.** We used the analytical dataset with 3 seeds, xgboost models with 100 trees, and evaluated on held-out data using residual MSE (%) (lower is better). The TreeHFD baseline was first reproduced against the paper's reference values; the reproduction passed within the registered tolerance, so the gate verdict was True. Only then were candidate improvements run.

**Ideas.** Three ideas were generated; two were run on the subset.

- **C1: Depth sweep ensemble.** Fit XGBTreeHFD at several depth_variable values (e.g. 2, 3, 4). For each interaction column, keep the candidate fit with lowest residual MSE on a validation split, reassembling components so each remains a function of only its own variables. Average predictions over seeds to reduce variance.
- **C3: Least-squares recalibration.** After the TreeHFD fit, take the component matrices M (intercept, main effects, interactions) and solve a constrained least-squares refit of coefficients against model predictions on training data (scipy.optimize.lsq_linear, nonnegative or free). The coefficients multiply each existing component, preserving each component's dependence on only its own variables.

Both ideas preserve the property that each component depends only on its own variables, which is required for a valid functional decomposition.

## Results

Mean ± std over 3 seeds on the analytical dataset:

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ |
|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 22.2 ± 0.29 |
| C1: Depth sweep ensemble | 3.23 ± 0.25 | 78.7 ± 9.1 |
| C3: Least-squares recalibration | 2.95 ± 0.35 | 27.9 ± 0.59 |

**Outcome.** No idea beat the baseline on every dataset. On the analytical dataset, the baseline TreeHFD achieved residual MSE of 2.79 ± 0.32. C1 (depth sweep ensemble) was worse at 3.23 ± 0.25 and roughly 3.5× slower in runtime. C3 (least-squares recalibration) was also worse at 2.95 ± 0.35, with a modest runtime increase. This is a negative result: neither candidate improved accuracy, and both added runtime cost.

## Limitations

This was a crude loop, and its conclusions are correspondingly narrow:

- **Scale.** Only one dataset (Analytical), 3 seeds, and one model configuration (xgboost with 100 trees) were used. Results may not transfer to other datasets, models, or settings.
- **Idea coverage.** Three ideas were generated but only two were implemented and run; the third was never tested.
- **Idea provenance.** The ideas were produced and implemented by a language model and were not deeply engineered; a stronger implementation of C1 or C3 might behave differently.
- **What was and was not established.** The loop established that the baseline reproduces within tolerance and that these two specific implementations, under this configuration, did not improve residual MSE on this dataset. It did not establish that the ideas are fundamentally inferior, that they cannot help on other datasets, or anything about statistical significance given only 3 seeds.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
[R3] Maria Keller, Tomas Ruiz. Adaptive Cartesian Priors for Additive Tree Explanations. 2024. arXiv:2408.83260.
