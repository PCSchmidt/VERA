## Abstract

We report a small, negative-result experiment on improving TreeHFD [R1], a method that decomposes an xgboost model [R2] into main effects and second-order interactions. We first reproduced the baseline within the registered tolerance (gate verdict True). A crude improvement loop generated three ideas, ran two of them, and neither beat the baseline on every dataset. Refitting the intercept residual (C3) made held-out residual MSE dramatically worse; depth-variable tuning (C2) improved the Analytical dataset but worsened Airfoil. We describe what the loop did and did not establish.

## Method

The problem: improve TreeHFD, which decomposes an xgboost model (100 trees) into main effects and second-order interactions. The metric is held-out Residual MSE (%), lower is better, reported on two datasets (Analytical, Airfoil) over 3 seeds.

The baseline reproduction matched the paper's reference values within the registered tolerance, so the pipeline was accepted as faithful to the paper's convention. Note that the paper's convention reports in-sample residual MSE (Analytical 0.570; Airfoil 1.52); our results table uses held-out data, so values are higher.

Two ideas were implemented out of three generated:

- **C3: Refit intercept residual.** After TreeHFD's fit, compute the residual r = model(X) − sum(components) on training data, add the mean residual to the intercept, and optionally refit the largest interaction components (via treehfd refit or ridge on their variables) to the residual. Each refit maps only its own component's variables to output, keeping additivity.
- **C2: Depth-variable tuning.** Sweep depth_variable over several values (e.g., 2, 3, 4, 5) on training data, evaluate held-out Residual MSE for each, and select the best. Deeper variable selection changes which splits define main effects, often reducing the unexplained residual. Only the chosen configuration is used for the final fit.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.2 ± 0.97 | 4.73 ± 0.11 | 3.49 ± 0.094 |
| C3: Refit intercept residual | 31.3 ± 2.6 | 30.9 ± 0.48 | 36581 ± 1750 | 3.77 ± 0.14 |
| C2: Depth-variable tuning | 2.41 ± 0.16 | 52.2 ± 3.1 | 5.15 ± 0.66 | 10.2 ± 0.63 |

No idea beat the baseline on every dataset. C3 was clearly harmful: held-out Residual MSE rose to 31.3 on Analytical and to 36581 on Airfoil, far above the baseline's 2.79 and 4.73. C2 was mixed: it improved Analytical (2.41 vs 2.79) but worsened Airfoil (5.15 vs 4.73), at roughly double the runtime on Airfoil (10.2 vs 3.43 s) and higher runtime on Analytical (52.2 vs 27.2 s).

## Limitations

This was a crude loop, and the conclusions are correspondingly narrow. It used only 3 seeds, two datasets, and one model configuration (xgboost with 100 trees). The three ideas were generated and the two run were implemented by a language model, without human iteration or tuning; C3 in particular may have failed for fixable reasons (e.g., how the refits were weighted or regularized) that this run did not diagnose. C2's mixed result may reflect dataset-specific sensitivity of depth_variable rather than a general effect. The loop also did not establish anything about the paper's in-sample convention, where the baseline is much lower (Analytical 0.570; Airfoil 1.52); all comparisons here are on held-out data. We therefore report this as a negative result: neither implemented idea improved TreeHFD across both datasets, and no claim is made beyond the configurations tested.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
