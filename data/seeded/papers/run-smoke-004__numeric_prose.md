## Abstract

TreeHFD decomposes an XGBoost model into main effects and second-order interactions [R1]. We report a small, automated attempt to improve its accuracy on an analytical benchmark. Two ideas generated in a crude research loop were implemented and run: a depth sweep ensemble that selects per-interaction candidates across decomposition depths, and a least-squares recalibration of component coefficients. Neither beat the TreeHFD baseline on every dataset; the baseline's residual MSE was lowest. We describe plainly what this run did and did not establish.

## Method

The baseline TreeHFD pipeline was first reproduced against the paper's reference values on the analytical dataset, using XGBoost with 100 trees [R2], and passed the registered tolerance check. Evaluation used 3 seeds and held-out data; the metric is Residual MSE (%), lower is better.

Three improvement ideas were generated; two were run on the subset:

- **C1: Depth sweep ensemble.** Fit XGBTreeHFD at several depth_variable values (e.g. 2, 3, 4). For each interaction column, keep the candidate fit with lowest residual MSE on a validation split, reassembling components so each remains a function of only its own variables. Average predictions over seeds to reduce variance.
- **C3: Least-squares recalibration.** After the TreeHFD fit, take the component matrices M (intercept, main effects, interactions) and solve a constrained least-squares refit of coefficients against model predictions on the training data (scipy.optimize.lsq_linear, nonnegative or free). Coefficients multiply each existing component, so each component's dependence on only its own variables is preserved.

Both ideas preserve the structural constraint that each component depends only on its own variables.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ |
|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 22.2 ± 0.29 |
| C1: Depth sweep ensemble | 3.23 ± 0.25 | 78.7 ± 9.1 |
| C3: Least-squares recalibration | 2.95 ± 0.35 | 27.9 ± 0.59 |

No idea beat the baseline on every dataset. On the analytical dataset, the baseline achieved the lowest mean residual MSE (2.79 ± 0.32). C3 (2.95 ± 6.35) was within roughly one standard deviation of the baseline, but this is a negative result, not an improvement: the loop's acceptance criterion was not met. C1 was both less accurate (3.23 ± 0.25) and much slower (78.7 ± 9.1 s versus 22.2 ± 0.29 s), as expected from fitting several decompositions. C3 added modest runtime (27.9 ± 0.59 s) for no accuracy gain.

## Limitations

This was a crude loop, and its conclusions are correspondingly narrow:

- **Scale.** Only one dataset (Analytical), 3 seeds, and one model configuration (XGBoost with 100 trees) were used. Results may not transfer to other datasets, larger models, or higher-order interactions.
- **Idea generation.** The ideas were produced and implemented by a language model in an automated loop, without human iteration or tuning; both were run essentially as first drafts.
- **Coverage.** Three ideas were generated but only two were run; the third was never evaluated.
- **What was not established.** The run does not show that TreeHFD cannot be improved, only that these two specific, unrefined ideas did not improve it under this configuration. In particular, C3's near-baseline result with a single least-squares pass leaves open whether recalibration could help with better constraints or regularization, but this run provides no evidence for it.
- **Statistics.** With 3 seeds, the standard deviations are noisy, and no formal significance testing was performed.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
