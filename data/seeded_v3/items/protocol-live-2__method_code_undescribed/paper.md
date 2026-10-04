## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A language model proposed three ideas, and two were run: residual backfitting refit (C2) and interaction screening by strength (C1). Neither beat the baseline on every dataset. On held-out Residual MSE (%), C2 was slightly worse than TreeHFD on both datasets, and C1 was worse on Analytical and tied on Airfoil. This is a negative result. A registered protocol also compared the methods with TreeSHAP across correlation levels on the analytical function. In that protocol C1 had lower component error than TreeHFD at every correlation level, though the differences are small relative to the seed spread at several levels.

## Related work

The TreeHFD paper frames the problem as one of dependence. The Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. Another source describes the generalized decomposition as existing and unique under bounded-density assumptions, with its geometry still implicit [R35].

On accuracy, TreeHFD's own experiments show that it approximates the decomposition of fitted xgboost models well on real data, and that its components are nearly hierarchically orthogonal while TreeSHAP's are often entangled [R5]. For random forests, its authors report lower accuracy than with xgboost in an analytical case [R5]. Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10][R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled.

Evidence on TreeSHAP under correlation is partial. One construction shows exact TreeSHAP giving unequal importance to interchangeable redundant channels [R6]. A neural-network study found that correlation may greatly increase attribution variance [R41]. TreeHFD is computationally limited to shallow trees [R15] and inherits any overfitting of the ensemble [R5]. No source measures error against known components across a correlation sweep, or bootstrap-refit rank stability of component importances.

## Method

TreeHFD is fitted to an xgboost model [R101] with 100 trees. Two candidate changes were implemented and run:

- **C2, residual backfitting refit.** After the TreeHFD fit on training data, compute the residual between the model predictions and the component sum. Fit a per-component smoother (a shallow gradient-boosted tree or spline) on only that component's variables, and add it to that component. Repeat for 2-3 rounds.
- **C1, interaction screening by strength.** Fit TreeHFD with main effects only, or a cheap run. Rank variable pairs by interaction-component variance or by co-occurrence in tree paths, then refit with the interaction list restricted to the top-K pairs.

Three ideas were generated and two were run on the subset. The metric is Residual MSE (%), lower is better, on held-out data, over 3 seeds, on Analytical and Airfoil.

The baseline was reproduced against the paper's reference values within the registered tolerance (gate verdict True). The reproduction used the paper's in-sample convention, giving a residual MSE of 0.570% on Analytical and 1.52% on Airfoil. The results table reports held-out values, which are higher.

A registered protocol was written down, dated and hashed before any run. It covered TreeHFD, TreeSHAP (xgboost's path-dependent TreeSHAP with interaction values), C2 and C1. It used Analytical at rho 0, 0.25, 0.5, 0.75, 0.9 and 0.95, plus Airfoil, with 3 seeds and 5 bootstrap refits of the ensemble per seed. Component error compares components with the true decomposition of the analytical function, whose closed form was checked against the TreeHFD paper's Table 3. Airfoil has no true components. Rank stability is the mean Spearman correlation of component importances between bootstrap refits. No cells were uncomputable.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 29.8 ± 0.65 | 4.73 ± 0.11 | 3.26 ± 0.054 |
| C2: Residual backfitting refit | 2.87 ± 0.32 | 38.7 ± 0.30 | 4.81 ± 0.18 | 5.14 ± 0.21 |
| C1: Interaction screening by strength | 3.01 ± 0.40 | 21.1 ± 0.58 | 4.73 ± 0.11 | 3.92 ± 0.19 |

Mean ± std over 3 seeds; stability from 5 bootstrap refits each.

**Component error against the true decomposition (% of signal variance)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ |
|---|---|---|---|---|---|---|
| TreeHFD | 8.52 ± 0.23 | 7.15 ± 0.35 | 5.99 ± 0.21 | 3.93 ± 0.22 | 3.05 ± 0.23 | 2.99 ± 0.27 |
| TreeSHAP | 7.94 ± 0.40 | 20.4 ± 0.56 | 34.0 ± 2.8 | 29.9 ± 0.44 | 27.1 ± 2.9 | 28.2 ± 2.1 |
| C2: Residual backfitting refit | 8.49 ± 0.24 | 7.09 ± 0.33 | 5.89 ± 0.21 | 3.87 ± 0.21 | 3.04 ± 0.24 | 2.97 ± 0.25 |
| C1: Interaction screening by strength | 7.60 ± 0.40 | 6.35 ± 0.14 | 5.74 ± 0.69 | 3.58 ± 0.21 | 2.67 ± 0.13 | 2.47 ± 0.19 |

**Rank stability of component importances across bootstrap refits (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ | Airfoil ↑ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 0.867 ± 0.037 | 0.948 ± 0.017 | 0.937 ± 0.010 | 0.936 ± 0.018 | 0.866 ± 0.019 | 0.800 ± 0.052 | 0.987 ± 0.0024 |
| TreeSHAP | 0.877 ± 0.022 | 0.923 ± 0.0018 | 0.913 ± 0.00032 | 0.907 ± 0.019 | 0.914 ± 0.0081 | 0.872 ± 0.012 | 0.988 ± 0.0037 |
| C2: Residual backfitting refit | 0.868 ± 0.036 | 0.946 ± 0.016 | 0.937 ± 0.015 | 0.934 ± 0.017 | 0.866 ± 0.018 | 0.796 ± 0.053 | 0.986 ± 0.0023 |
| C1: Interaction screening by strength | 0.871 ± 0.024 | 0.934 ± 0.0043 | 0.906 ± 0.021 | 0.924 ± 0.012 | 0.923 ± 0.0057 | 0.853 ± 0.057 | 0.987 ± 0.0024 |

**Rank agreement of component importances with the true ones (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ |
|---|---|---|---|---|---|---|
| TreeHFD | 0.397 ± 0.051 | 0.881 ± 0.0071 | 0.639 ± 0.034 | 0.636 ± 0.010 | 0.684 ± 0.074 | 0.699 ± 0.072 |
| TreeSHAP | 0.415 ± 0.033 | 0.869 ± 0.034 | 0.643 ± 0.017 | 0.778 ± 0.039 | 0.682 ± 0.030 | 0.712 ± 0.043 |
| C2: Residual backfitting refit | 0.396 ± 0.052 | 0.877 ± 0.0043 | 0.641 ± 0.035 | 0.635 ± 0.0090 | 0.688 ± 0.068 | 0.699 ± 0.072 |
| C1: Interaction screening by strength | 0.339 ± 0.067 | 0.847 ± 0.043 | 0.612 ± 0.034 | 0.767 ± 0.030 | 0.709 ± 0.041 | 0.728 ± 0.028 |

**Residual MSE against the fitted ensemble (%)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 5.54 ± 0.40 | 3.80 ± 0.52 | 2.79 ± 0.32 | 1.66 ± 0.084 | 1.11 ± 0.19 | 1.03 ± 0.022 | 4.73 ± 0.11 |
| TreeSHAP | 0.0000000000556 ± 0.0000000000055 | 0.0000000000608 ± 0.0000000000052 | 0.0000000000523 ± 0.0000000000088 | 0.0000000000418 ± 0.0000000000098 | 0.0000000000495 ± 0.0000000000012 | 0.0000000000620 ± 0.000000000015 | 0.00000000265 ± 0.00000000023 |
| C2: Residual backfitting refit | 5.63 ± 0.41 | 3.90 ± 0.51 | 2.87 ± 0.32 | 1.68 ± 0.080 | 1.16 ± 0.23 | 1.04 ± 0.0076 | 4.81 ± 0.18 |
| C1: Interaction screening by strength | 5.25 ± 0.66 | 3.44 ± 0.33 | 3.01 ± 0.40 | 1.57 ± 0.061 | 0.975 ± 0.13 | 0.791 ± 0.11 | 4.73 ± 0.11 |

**Runtime of the decomposition call (s)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 39.8 ± 1.3 | 38.7 ± 1.8 | 36.6 ± 0.12 | 34.2 ± 2.3 | 29.9 ± 2.8 | 28.8 ± 1.6 | 4.41 ± 0.25 |
| TreeSHAP | 3.04 ± 0.31 | 2.85 ± 0.053 | 2.69 ± 0.085 | 3.23 ± 0.10 | 3.00 ± 0.14 | 2.86 ± 0.12 | 0.266 ± 0.014 |
| C2: Residual backfitting refit | 50.3 ± 1.5 | 48.1 ± 1.8 | 46.0 ± 1.5 | 42.5 ± 1.4 | 38.5 ± 0.47 | 35.9 ± 1.4 | 6.49 ± 0.34 |
| C1: Interaction screening by strength | 33.2 ± 6.4 | 32.5 ± 6.8 | 31.2 ± 5.2 | 24.6 ± 5.5 | 18.9 ± 0.85 | 18.6 ± 0.47 | 4.79 ± 0.034 |

![Figure 1](figures/fig_component_mse_pct.png)

Figure 1. Component error against the true decomposition, by method and correlation level.

![Figure 2](figures/fig_rank_stability.png)

Figure 2. Rank stability of component importances across bootstrap refits.

![Figure 3](figures/fig_residual_mse_pct.png)

Figure 3. Residual MSE (%) by method and dataset (held-out).

**Primary metric.** In Figure 3 and the first table, no idea beat the baseline on any registered dataset. C2 gave 2.87 against 2.79 on Analytical and 4.81 against 4.73 on Airfoil, differences well within the seed spread. C1 gave 3.01 on Analytical (worse) and 4.73 on Airfoil (identical). C2 was also slower on both datasets. C1 was faster on Analytical (21.1 s against 29.8 s) but slower on Airfoil (3.92 s against 3.26 s). Because nothing beat the baseline on the primary metric, no ablation was run.

**Baseline trends.** As Figure 1 shows, TreeHFD's component error against the truth falls as correlation rises, from 8.52% of signal variance at rho 0 to 2.99% at rho 0.95. Its residual MSE against the fitted ensemble also falls, from 5.54% to 1.03%. Lower residual and lower component error at high correlation is not obviously expected, and the paper should remark on it. This work does not explain it. In Figure 2, its rank stability is lowest at rho 0.95 (0.800) and at rho 0 (0.867), and its rank agreement with the true importances is lowest at rho 0 (0.397).

**Protocol secondary results.** In Figure 1, TreeSHAP's component error is similar to TreeHFD's at rho 0 (7.94 against 8.52) but much larger at every correlation from 0.25 up (20.4 to 34.0). TreeSHAP's residual against the ensemble is essentially zero, and it is the fastest method. In Figure 2, TreeSHAP rank stability is higher than TreeHFD's at rho 0.9 and 0.95. C1 has the lowest component error at every rho (for example 2.47 against 2.99 at rho 0.95), but the gaps are within roughly one to two standard deviations at several levels. C1's rank agreement with the true importances is lower than TreeHFD's at rho 0 and 0.5. C2 is nearly indistinguishable from TreeHFD on every protocol metric and costs more time.

## Limitations

- Only 3 seeds, two datasets, and one model configuration (xgboost with 100 trees) were used.
- The ideas were produced and implemented by a language model in a crude loop, with no tuning of K or of the smoothers.
- The primary metric is held-out residual MSE, which measures fit of the component sum to the model, not whether the components are correct. The conclusion of no improvement rests on that metric.
- The component-error improvements for C1 are secondary protocol results that were not the selection criterion, and many are within noise.
- Relative to the research question: the experiments address (a) component error against ground truth across rho 0 to 0.95, for TreeHFD and TreeSHAP on one analytical function with xgboost, and (b) bootstrap rank stability of component importances for those methods on that function and on Airfoil. They do not address random forests, since only xgboost was used. They do not address California Housing or Adult, or top-k component stability there. Airfoil has no ground truth. Other interaction structures were not tested.
- Whether TreeHFD's advantage persists in other settings is untested here.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
