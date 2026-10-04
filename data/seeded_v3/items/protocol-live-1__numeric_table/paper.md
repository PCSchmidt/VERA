## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A language-model research loop generated 3 ideas and ran 1 of them, C2 (deeper variable selection). It was tested on Analytical and Airfoil data with 3 seeds, and under a registered protocol that also compared TreeHFD and TreeSHAP across correlation levels. The result is negative: no idea beat the baseline on every dataset. C2 had higher held-out residual MSE than the baseline on both datasets. It was faster on Analytical and slower on Airfoil. No ablation was run.

## Related work

The TreeHFD paper treats correlated inputs as a problem of dependence. The Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. Another source says the generalized decomposition exists and is unique under bounded-density assumptions, though its geometry is still implicit [R35].

On accuracy, TreeHFD's own experiments show it approximates the decomposition of fitted xgboost models well on real data. It reports that TreeHFD's components are nearly hierarchically orthogonal while TreeSHAP's are often entangled [R5]. These are orthogonality and residual measures on fitted models, not errors against ground-truth components across a correlation sweep.

Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10][R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy. Evidence on TreeSHAP under correlation is partial: exact TreeSHAP can give unequal importance to interchangeable redundant channels [R6], and a neural-network study found that correlation may greatly increase attribution variance [R41]. TreeHFD is limited to shallow trees [R15] and inherits any overfitting of the underlying ensemble [R5].

## Method

The baseline is TreeHFD on an xgboost model [R101] with 100 trees. Datasets were Analytical and Airfoil, with 3 seeds and held-out data. The metric is residual MSE (%), lower is better. The baseline was reproduced against the paper's reference values [R5] within the registered tolerance (gate verdict True). The reproduction used the paper's in-sample convention on both datasets: residual MSE was 0.570 on Analytical and 1.52 on Airfoil. The results table reports held-out values, which are higher, so the two are not directly comparable.

C2 sets depth_variable higher than the default in XGBTreeHFD.fit, so variables are selected from deeper tree structure. Values 1 to 3 were compared on validation data and the one with the lowest held-out residual MSE was chosen.

A protocol was registered (written down, dated and hashed before any run). Methods: TreeHFD, TreeSHAP and C2. Datasets: Analytical at rho 0, 0.25, 0.5, 0.75, 0.9 and 0.95, plus Airfoil. It used 3 seeds and 5 bootstrap refits per seed. Component error is measured against the true decomposition of the analytical function, which has a closed form checked against the TreeHFD paper's Table 3. Airfoil has no true components. Rank stability is the mean Spearman correlation of component importances between refits. TreeSHAP is xgboost's path-dependent TreeSHAP with interaction values. No cells were invalid.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 29.8 ± 0.65 | 4.73 ± 0.11 | 3.26 ± 0.054 |
| C2: Deeper variable selection | 4.72 ± 1.0 | 16.5 ± 1.5 | 6.38 ± 0.57 | 5.62 ± 0.28 |

Mean ± std over 3 seeds; stability from 5 bootstrap refits each.

**Component error against the true decomposition (% of signal variance)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ |
|---|---|---|---|---|---|---|
| TreeHFD | 8.52 ± 0.23 | 7.15 ± 0.35 | 5.99 ± 0.21 | 3.93 ± 0.22 | 3.05 ± 0.23 | 2.99 ± 0.27 |
| TreeSHAP | 7.94 ± 0.40 | 20.4 ± 0.56 | 34.0 ± 2.8 | 29.9 ± 0.44 | 27.1 ± 2.9 | 28.2 ± 2.1 |
| C2: Deeper variable selection | 8.91 ± 1.2 | 8.15 ± 1.3 | 8.39 ± 1.0 | 4.65 ± 1.1 | 2.82 ± 0.54 | 3.47 ± 0.76 |

**Rank stability of component importances across bootstrap refits (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ | Airfoil ↑ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 0.867 ± 0.037 | 0.948 ± 0.017 | 0.937 ± 0.010 | 0.936 ± 0.018 | 0.866 ± 0.019 | 0.800 ± 0.052 | 0.987 ± 0.0024 |
| TreeSHAP | 0.877 ± 0.022 | 0.923 ± 0.0018 | 0.913 ± 0.00032 | 0.907 ± 0.019 | 0.914 ± 0.0081 | 0.872 ± 0.012 | 0.988 ± 0.0037 |
| C2: Deeper variable selection | 0.705 ± 0.016 | 0.838 ± 0.014 | 0.876 ± 0.0057 | 0.879 ± 0.0090 | 0.884 ± 0.0054 | 0.852 ± 0.033 | 0.979 ± 0.0021 |

**Rank agreement of component importances with the true ones (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ |
|---|---|---|---|---|---|---|
| TreeHFD | 0.397 ± 0.051 | 0.881 ± 0.0071 | 0.639 ± 0.034 | 0.636 ± 0.010 | 0.684 ± 0.074 | 0.699 ± 0.072 |
| TreeSHAP | 0.415 ± 0.033 | 0.869 ± 0.034 | 0.643 ± 0.017 | 0.778 ± 0.039 | 0.682 ± 0.030 | 0.712 ± 0.043 |
| C2: Deeper variable selection | 0.388 ± 0.045 | 0.787 ± 0.041 | 0.613 ± 0.033 | 0.763 ± 0.024 | 0.695 ± 0.059 | 0.767 ± 0.054 |

**Residual MSE against the fitted ensemble (%)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 5.54 ± 0.40 | 3.80 ± 0.52 | 2.79 ± 0.32 | 1.66 ± 0.084 | 1.11 ± 0.19 | 1.03 ± 0.022 | 4.73 ± 0.11 |
| TreeSHAP | 0.0000000000556 ± 0.0000000000055 | 0.0000000000608 ± 0.0000000000052 | 0.0000000000523 ± 0.0000000000088 | 0.0000000000418 ± 0.0000000000098 | 0.0000000000495 ± 0.0000000000012 | 0.0000000000620 ± 0.000000000015 | 0.00000000265 ± 0.00000000023 |
| C2: Deeper variable selection | 4.59 ± 0.51 | 5.09 ± 0.89 | 4.72 ± 1.0 | 2.59 ± 0.59 | 1.19 ± 0.092 | 1.06 ± 0.30 | 6.38 ± 0.57 |

**Runtime of the decomposition call (s)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 02.5 ± 5.5 | 40.4 ± 4.0 | 37.0 ± 5.4 | 35.2 ± 4.0 | 31.8 ± 4.3 | 31.1 ± 4.7 | 5.34 ± 0.34 |
| TreeSHAP | 2.51 ± 0.21 | 3.09 ± 0.090 | 2.63 ± 0.18 | 2.63 ± 0.31 | 2.86 ± 0.10 | 3.24 ± 0.060 | 0.270 ± 0.014 |
| C2: Deeper variable selection | 16.7 ± 1.9 | 17.4 ± 0.56 | 17.5 ± 1.0 | 17.9 ± 1.8 | 17.2 ± 0.47 | 16.5 ± 1.5 | 6.14 ± 0.46 |

Figure 1 shows component error against the true decomposition by method and correlation.

![Figure 1](figures/fig_component_mse_pct.png)

Figure 1. Component error against the true decomposition (% of signal variance) by method and correlation.

Figure 2 shows rank stability of component importances across bootstrap refits.

![Figure 2](figures/fig_rank_stability.png)

Figure 2. Rank stability of component importances across bootstrap refits.

Figure 3 shows held-out residual MSE by method and dataset.

![Figure 3](figures/fig_residual_mse_pct.png)

Figure 3. Residual MSE (%) by method and dataset (held-out).

**Main comparison.** C2 did not beat the baseline (Figure 3): held-out residual MSE was 4.72 vs 2.79 on Analytical and 6.38 vs 4.73 on Airfoil. Runtime was lower on Analytical (16.5 s vs 29.8 s) but higher on Airfoil (5.62 s vs 3.26 s). Since it lost on the primary metric on both datasets, no ablation was run.

**Trends in the baseline.** TreeHFD's own residual MSE falls as correlation rises, from 5.54 at rho 0 to 1.03 at 0.95. Its component error against the truth also falls, from 8.52 to 2.99 (Figure 1). Higher correlation therefore did not make TreeHFD worse on these measures. We did not investigate why, and the paper should remark on it. TreeHFD's rank stability (Figure 2) is not monotone: 0.948 at rho 0.25 and 0.800 at 0.95.

**TreeHFD vs TreeSHAP.** TreeSHAP's component error is similar to TreeHFD's at rho 0 (7.94 vs 8.52) but much larger at higher correlation (34.0 vs 5.99 at rho 0.5, and 28.2 vs 2.99 at 0.95). TreeSHAP's residual MSE is essentially zero, as expected for an exact additive attribution of the model, so low residual does not imply accurate components. TreeSHAP's rank stability is higher than TreeHFD's at rho 0.9 and 0.95 (0.914 vs 0.866, 0.872 vs 0.800). Rank agreement with the true importances is mixed, with no consistent winner between the two.

**C2 in the protocol.** C2's component error is within noise of TreeHFD at several correlations, and numerically lower at rho 0.9 (2.82 vs 3.05, with std 0.54 and 0.23). Its rank stability is lower than the baseline's at most levels, and its residual MSE is higher at most levels.

## Limitations

- Only 3 seeds, two datasets, one xgboost configuration (100 trees), and one idea run out of three. Differences within the stated standard deviations should not be read as real.
- Ideas were produced and implemented by a language model, and the implementation may be imperfect.
- The main table is held-out while the paper's convention is in-sample, so the numbers differ.
- Relative to the research question, these experiments address component error against known components and bootstrap rank stability across rho 0 to 0.95, on an analytical function with xgboost. They do not cover random forests, California housing or Adult, or top-k component stability on public datasets. Airfoil has only rank stability and residual MSE, with no ground truth.
- The reason for the trends across correlation was not tested.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
