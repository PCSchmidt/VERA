## Abstract

TreeHFD decomposes an xgboost model [R2] into main effects and second-order interactions [R1]. We report a small improvement attempt over the TreeHFD baseline, run as a crude automated research loop. Three ideas were generated and two were implemented and run: refitting the intercept residual (C3) and tuning the depth-variable parameter (C2). The baseline was first reproduced against the paper's reference values within the registered tolerance. Neither idea beat the baseline on every dataset: C3 substantially worsened held-out residual MSE, while C2 improved the Analytical dataset but slightly worsened Airfoil. We therefore report a negative result. The loop was small (two datasets, three seeds, one model configuration, ideas produced and implemented by a language model), so its conclusions are limited.

## Method

The task was to improve TreeHFD, which decomposes an xgboost model (100 trees) into main effects and second-order interactions [R1]. Evaluation used two datasets (Analytical, Airfoil), 3 seeds, held-out data, and Residual MSE (%) as the metric, lower is better. The paper's convention reports in-sample residual MSE; the baseline reproduced against the paper's reference values within the registered tolerance (gate verdict True), with in-sample residual MSE of 0.570 on Analytical and 1.52 on Airfoil. The results table below shows held-out values, which are higher.

Three ideas were generated; two were run on the subset:

- **C3: Refit intercept residual.** After TreeHFD's fit, compute the residual r = model(X) − sum(components) on training data. Add the mean residual to the intercept, and optionally refit the largest interaction components (via treehfd refit or ridge on their variables) to the residual. Each refit maps only its own component's variables to output, keeping additivity while shrinking held-out residual MSE.
- **C2: Depth-variable tuning.** Sweep depth_variable over several values (e.g., 2, 3, 4, 5) on training data, evaluate held-out Residual MSE for each, and select the best. Deeper variable selection changes which splits define main effects, often reducing the unexplained residual. Only the chosen configuration is used for the final fit; all components remain functions of their own variables.

The third idea was generated but not run. The outcome was that no idea beat the baseline on every dataset.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.2 ± 0.97 | 4.73 ± 0.11 | 3.49 ± 0.094 |
| C3: Refit intercept residual | 31.3 ± 2.6 | 30.9 ± 0.48 | 36581 ± 1750 | 3.77 ± 0.14 |
| C2: Depth-variable tuning | 2.41 ± 0.16 | 52.2 ± 3.1 | 5.15 ± 0.66 | 10.2 ± 0.63 |

C3 (Refit intercept residual) failed badly on held-out data: residual MSE rose to 31.3 ± 2.6 on Analytical and 36581 ± 1750 on Airfoil, versus 2.79 ± 0.32 and 4.73 ± 0.11 for the baseline. A plausible reading is that correcting the intercept on training residuals does not generalize to held-out data, but the loop did not diagnose the failure, so this is an interpretation, not an established cause.

C2 (Depth-variable tuning) improved the Analytical dataset (2.41 ± 0.16 vs 2.79 ± 0.32) but worsened Airfoil (5.15 ± 0.66 vs 4.73 ± 0.11), at roughly 2–4× the baseline runtime on both datasets (52.2 ± 3.1 vs 27.2 ± 0.97 seconds on Analytical; 10.2 ± 0.63 vs 3.49 ± 0.094 seconds on Airfoil). The improvement on Analytical is within about one standard deviation of the baseline, so it should not be treated as a robust gain.

In summary: no idea beat the baseline on every dataset. This is a negative result, reported as such.

## Limitations

- The loop was crude and small: two datasets, 3 seeds, one model configuration (xgboost with 100 trees), and only 2 of 3 generated ideas were implemented and run.
- The ideas were produced and implemented by a language model, without human experimental design or follow-up debugging; failures such as C3's were not diagnosed.
- Baseline reproduction was checked against the paper's in-sample convention; the comparison among methods used held-out values, which are higher, so the table's baseline numbers are not directly comparable to the paper's reference values.
- No idea was validated beyond these two datasets or this single model configuration; C2's Analytical gain is not statistically distinguishable from the baseline at 3 seeds.
- The loop did not establish why C3 failed, nor whether a corrected version of C3 or additional tuning of C2 could beat the baseline.

## References

[R1] Clément Bénard. Forest Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
