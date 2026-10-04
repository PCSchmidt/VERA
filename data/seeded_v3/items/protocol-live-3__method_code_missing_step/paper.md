# Improving TreeHFD: two ideas, no improvement

## Abstract

TreeHFD decomposes a tree ensemble into main effects and second-order interactions [R5]. We ran a crude automated research loop to try to improve its residual decomposition error. The baseline reproduction passed the registered tolerance gate on both datasets (in-sample residual MSE, the paper's convention: Analytical 0.570%, Airfoil 1.52%; the results table reports held-out values, which are higher). Three ideas were generated and two were implemented and tested against the baseline: (C2) sweeping the variable-selection depth parameter over a validation split, and (C3) a residual refit calibration that fits a small per-component ridge correction on training residuals. No idea beat the baseline on every dataset; C3 was essentially indistinguishable from the baseline, and C2 was substantially worse. No ablation was run because no idea beat the baseline on the primary metric on any registered dataset. The baseline's own results show residual MSE and component error both decreasing as feature correlation rises. What this loop establishes is narrow: two specific modifications, on two datasets, with three seeds and one model configuration, do not improve TreeHFD. It does not establish that no improvement exists.

## Related work

TreeHFD decomposes tree ensembles via the Hoeffding functional decomposition, generalized to dependent inputs through hierarchical orthogonality constraints [R5]. The Hoeffding decomposition is unique only for independent inputs; under dependence, mutual orthogonality generally fails [R10]. The generalized decomposition exists and is unique under bounded-density assumptions, but its geometry remains implicit [R35]. TreeHFD's own experiments show good approximation of fitted xgboost decompositions on real data, with components nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R5]. Other work reports close agreement between TreeSHAP and HFD-style global rankings across datasets [R10], and high mean rank correlations with SHAP explainers [R35], contrasting with TreeHFD's characterization of TreeSHAP as noisy. Evidence on TreeSHAP under correlation is partial: one construction shows exact TreeSHAP assigning unequal importance to interchangeable redundant channels [R6], and a neural-network study suggests correlation may increase attribution variance [R41]. Known limits of TreeHFD include computational restriction to shallow trees and the non-empty-leaves assumption [R15], and inheritance of the ensemble's overfitting [R5]. No supplied source measures error against known components across a correlation sweep from 0 to 0.95, nor bootstrap-refit rank stability of component importances [R5][R10][R35].

## Method

We followed a registered protocol, written down, dated and hashed before any run. Methods compared: TreeHFD [R5], TreeSHAP (xgboost's path-dependent variant with interaction values), and two modifications produced by the loop's idea stage:

- **C2: Vary depth_variable.** Sweep TreeHFD's variable-selection depth over several values (e.g., 2, 3, 4, None) on a validation split and pick the depth minimizing residual MSE. A final step rescales every component by its bootstrap standard deviation. Rationale: this depth controls which features enter each component, so a tuned depth may yield components that better explain the model's predictions.
- **C3: Residual refit calibration.** After TreeHFD's predict, compute the residual (model prediction minus summed components) on training data and fit a small correction — ridge regression of the residual on each component's own variables only, added back per component. Rationale: recalibrate each component while keeping it a function of its own variables.

Datasets: the Analytical benchmark (true main effects and one pairwise interaction, ground truth in closed form checked against the TreeHFD paper's Table 3 [R5]) at correlations rho from 0 to 0.95, and Airfoil (no true components). Models: xgboost [R101] with 100 trees. Three seeds per configuration, five bootstrap refits of the ensemble per seed for stability. Metrics: held-out residual MSE against the fitted ensemble, component error against the true decomposition (% of signal variance), and Spearman rank stability and rank agreement of component importances. No cells were uncomputable (0 invalid).

## Results

The baseline reproduced against the paper's reference values within the registered tolerance (gate verdict True). Note the row set: the reproduced values are in-sample residual MSE under the paper's convention — Analytical 0.570%, Airfoil 1.52% — while the results table below shows held-out values, which are higher for both datasets.

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 29.8 ± 0.65 | 4.73 ± 0.11 | 3.26 ± 0.054 |
| C2: Vary depth_variable | 12.8 ± 1.8 | 40.6 ± 0.74 | 22.7 ± 0.91 | 9.23 ± 0.38 |
| C3: Residual refit calibration | 2.80 ± 0.32 | 37.0 ± 0.57 | 4.73 ± 0.11 | 4.82 ± 0.25 |

Three ideas were generated; two were run on the subset. **No idea beat the baseline on every dataset.** C2 substantially worsened held-out residual MSE on both datasets and was slower (Figure 3 shows this gap). C3's residual MSE was within noise of the baseline on both datasets, and its component error (Figure 1) and rank stability (Figure 2) were likewise essentially unchanged — the ridge correction was too small to matter. Because no idea beat the baseline on the primary metric on any registered dataset, no ablation was run.

Mean ± std over 3 seeds; stability from 5 bootstrap refits each.

**Component error against the true decomposition (% of signal variance)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ |
|---|---|---|---|---|---|---|
| TreeHFD | 8.52 ± 0.23 | 7.15 ± 0.35 | 5.99 ± 0.21 | 3.93 ± 0.22 | 3.05 ± 0.23 | 2.99 ± 0.27 |
| TreeSHAP | 7.94 ± 0.40 | 20.4 ± 0.56 | 34.0 ± 2.8 | 29.9 ± 0.44 | 27.1 ± 2.9 | 28.2 ± 2.1 |
| C2: Vary depth_variable | 15.0 ± 2.6 | 13.7 ± 1.7 | 14.7 ± 2.6 | 8.97 ± 0.68 | 5.81 ± 1.4 | 11.2 ± 2.4 |
| C3: Residual refit calibration | 8.48 ± 0.24 | 7.13 ± 0.35 | 6.00 ± 0.21 | 3.93 ± 0.22 | 3.05 ± 0.23 | 2.99 ± 0.27 |

**Rank stability of component importances across bootstrap refits (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ | Airfoil ↑ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 0.867 ± 0.037 | 0.948 ± 0.017 | 0.937 ± 0.010 | 0.936 ± 0.018 | 0.866 ± 0.019 | 0.800 ± 0.052 | 0.987 ± 0.0024 |
| TreeSHAP | 0.877 ± 0.022 | 0.923 ± 0.0018 | 0.913 ± 0.00032 | 0.907 ± 0.019 | 0.914 ± 0.0081 | 0.872 ± 0.012 | 0.988 ± 0.0037 |
| C2: Vary depth_variable | 0.724 ± 0.031 | 0.767 ± 0.0094 | 0.793 ± 0.0067 | 0.850 ± 0.053 | 0.837 ± 0.017 | 0.821 ± 0.026 | 0.917 ± 0.021 |
| C3: Residual refit calibration | 0.867 ± 0.037 | 0.947 ± 0.015 | 0.936 ± 0.013 | 0.935 ± 0.017 | 0.869 ± 0.015 | 0.789 ± 0.044 | 0.987 ± 0.0024 |

**Rank agreement of component importances with the true ones (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ |
|---|---|---|---|---|---|---|
| TreeHFD | 0.397 ± 0.051 | 0.881 ± 0.0071 | 0.639 ± 0.034 | 0.636 ± 0.010 | 0.684 ± 0.074 | 0.699 ± 0.072 |
| TreeSHAP | 0.415 ± 0.033 | 0.869 ± 0.034 | 0.643 ± 0.017 | 0.778 ± 0.039 | 0.682 ± 0.030 | 0.712 ± 0.043 |
| C2: Vary depth_variable | 0.208 ± 0.044 | 0.623 ± 0.0072 | 0.681 ± 0.061 | 0.773 ± 0.030 | 0.696 ± 0.056 | 0.742 ± 0.099 |
| C3: Residual refit calibration | 0.397 ± 0.051 | 0.881 ± 0.0071 | 0.641 ± 0.035 | 0.636 ± 0.010 | 0.684 ± 0.074 | 0.699 ± 0.072 |

**Residual MSE against the fitted ensemble (%)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 5.54 ± 0.40 | 3.80 ± 0.52 | 2.79 ± 0.32 | 1.66 ± 0.084 | 1.11 ± 0.19 | 1.03 ± 0.022 | 4.73 ± 0.11 |
| TreeSHAP | 0.0000000000556 ± 0.0000000000055 | 0.0000000000608 ± 0.0000000000052 | 0.0000000000523 ± 0.0000000000088 | 0.0000000000418 ± 0.0000000000098 | 0.0000000000495 ± 0.0000000000012 | 0.0000000000620 ± 0.000000000015 | 0.00000000265 ± 0.00000000023 |
| C2: Vary depth_variable | 10.1 ± 2.0 | 11.4 ± 2.0 | 12.8 ± 1.8 | 6.57 ± 0.097 | 2.81 ± 0.15 | 2.78 ± 0.55 | 22.7 ± 0.91 |
| C3: Residual refit calibration | 5.56 ± 0.40 | 3.81 ± 0.52 | 2.80 ± 0.32 | 1.66 ± 0.083 | 1.11 ± 0.19 | 1.02 ± 0.021 | 4.73 ± 0.11 |

**Runtime of the decomposition call (s)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 38.1 ± 2.8 | 37.1 ± 0.81 | 34.6 ± 1.6 | 33.3 ± 0.84 | 27.6 ± 0.32 | 26.0 ± 0.80 | 4.12 ± 0.12 |
| TreeSHAP | 3.05 ± 0.17 | 2.74 ± 0.13 | 2.86 ± 0.27 | 3.13 ± 0.073 | 2.91 ± 0.34 | 2.95 ± 0.092 | 0.245 ± 0.028 |
| C2: Vary depth_variable | 55.1 ± 1.8 | 56.0 ± 0.70 | 54.1 ± 1.5 | 54.7 ± 0.82 | 46.8 ± 1.1 | 46.6 ± 2.3 | 12.2 ± 0.24 |
| C3: Residual refit calibration | 43.3 ± 0.72 | 42.4 ± 2.6 | 40.7 ± 2.0 | 40.4 ± 2.7 | 37.1 ± 0.93 | 34.1 ± 0.80 | 6.07 ± 0.14 |

![Figure 1](figures/fig_component_mse_pct.png)

Figure 1. Component error against the true decomposition (% of signal variance) by method and correlation level.

![Figure 2](figures/fig_rank_stability.png)

Figure 2. Rank stability of component importances across bootstrap refits (Spearman) by method and dataset.

![Figure 3](figures/fig_residual_mse_pct.png)

Figure 3. Held-out residual MSE (%) by method and dataset.

A trend worth remarking on in the baseline's own results: both residual MSE and component error decrease as correlation rises — residual MSE from 5.54% at rho 0 to 1.03% at rho 0.95, and component error from 8.52% to 2.99% of signal variance. TreeHFD thus appears most accurate on its own terms at high correlation, the regime the literature flags as hardest [R5][R35]. TreeSHAP, by contrast, has near-zero residual MSE (it reconstructs the ensemble almost exactly) but far larger component error at moderate-to-high correlation, confirming that reconstructing the model and recovering the true components are different goals [R6].

## Limitations

These experiments address only part of the research question. They do measure (a) component error against a known ground truth across rho from 0 to 0.95 and (b) bootstrap-refit rank stability, for one xgboost configuration on synthetic data — which the review identified as untested in the supplied sources [R5][R10][R35]. They do not address: random forests (only boosted ensembles), the proposed public-dataset comparisons (California housing, Adult), or top-k stability on real data; Airfoil is the only real dataset here and has no ground truth. The negative result is narrow: two ideas, implemented by a language model within a crude loop, on two datasets, three seeds, one model configuration (100 trees), and one ensemble per condition. We did not tune the ideas exhaustively, and C3's near-zero effect may reflect a correction that was simply too small rather than a flaw in the calibration concept. The improvement of TreeHFD's own metrics with increasing correlation deserves further study before any conclusion about robustness under dependence is drawn.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
