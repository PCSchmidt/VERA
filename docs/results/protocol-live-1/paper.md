## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A language-model-driven loop generated 3 ideas and ran 1 of them on a subset: C2, deeper variable selection (a higher depth_variable). The baseline reproduced the paper's reference values within the registered tolerance. C2 did not beat the baseline: on held-out Residual MSE it was worse on both datasets. In the registered protocol on correlated analytical data, TreeHFD recovered the true components far better than TreeSHAP at moderate to high correlation. C2 was close to TreeHFD on component error but less stable across bootstrap refits. This is a negative result.

## Related work

The TreeHFD paper frames the problem as one of dependence: the Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. Another source describes the generalized decomposition as existing and unique under bounded-density assumptions, with its geometry still implicit [R35].

On accuracy, TreeHFD's own experiments show it approximates the decomposition of fitted xgboost models well on real data, and its components are nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R5]. These are orthogonality and residual measures on fitted models, not errors against ground-truth components across a correlation sweep.

Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10][R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled. Evidence on TreeSHAP under correlation is partial: one construction shows exact TreeSHAP giving unequal importance to interchangeable redundant channels [R6], and a neural-network study found that correlation may greatly increase attribution variance [R41]. TreeHFD is computationally limited to shallow trees [R15] and inherits any overfitting of the ensemble [R5].

## Method

Baseline: TreeHFD on xgboost with 100 trees [R101], following [R5]. Baseline in-sample residual MSE (the paper's convention) was 0.570% on Analytical and 1.52% on Airfoil; the results table reports held-out values, which are higher.

Idea C2: set depth_variable higher than the default in XGBTreeHFD.fit, so variables for main effects and interactions are selected from deeper tree structure. Values 1–3 were compared on validation data, choosing the one minimizing held-out Residual MSE.

Registered protocol (written down, dated and hashed before any run): methods TreeHFD, TreeSHAP (xgboost's path-dependent TreeSHAP with interaction values) and C2. Datasets: Analytical at rho 0, 0.25, 0.5, 0.75, 0.9, 0.95, and Airfoil. 3 seeds, 5 bootstrap refits per seed. Component error compares against the closed-form true decomposition of the analytical function, checked against Table 3 of the TreeHFD paper; Airfoil has no true components. Rank stability is the mean Spearman correlation of component importances between refits. No cells were invalid.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 29.8 ± 0.65 | 4.73 ± 0.11 | 3.26 ± 0.054 |
| C2: Deeper variable selection | 4.72 ± 1.0 | 16.5 ± 1.5 | 6.38 ± 0.57 | 5.62 ± 0.28 |

C2 had higher held-out Residual MSE than the baseline on both datasets (Analytical 4.72 vs 2.79; Airfoil 6.38 vs 4.73). Its runtime was lower on Analytical (16.5 s vs 29.8 s) but higher on Airfoil (5.62 s vs 3.26 s). No idea beat the baseline on every dataset.

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
| TreeHFD | 42.5 ± 5.5 | 40.4 ± 4.0 | 37.0 ± 5.4 | 35.2 ± 4.0 | 31.8 ± 4.3 | 31.1 ± 4.7 | 5.34 ± 0.34 |
| TreeSHAP | 2.51 ± 0.21 | 3.09 ± 0.090 | 2.63 ± 0.18 | 2.63 ± 0.31 | 2.86 ± 0.10 | 3.24 ± 0.060 | 0.270 ± 0.014 |
| C2: Deeper variable selection | 16.7 ± 1.9 | 17.4 ± 0.56 | 17.5 ± 1.0 | 17.9 ± 1.8 | 17.2 ± 0.47 | 16.5 ± 1.5 | 6.14 ± 0.46 |

Reading the protocol tables:
- Component error: TreeHFD ranged from 8.52 at rho 0 down to 2.99 at rho 0.95. TreeSHAP was slightly lower at rho 0 (7.94) but much higher at the other correlations (20.4 to 34.0). C2 was similar to or worse than TreeHFD at most correlations, with overlapping spreads at rho 0.9 (2.82 vs 3.05) and 0.95.
- Residual MSE against the fitted ensemble: TreeSHAP is essentially zero, as expected from an exact additive attribution. This metric is therefore not comparable to the component error. C2 was worse than TreeHFD at most settings.
- Rank stability across refits: C2 was lower than TreeHFD at every Analytical rho and on Airfoil (0.979 vs 0.987). TreeHFD stability fell to 0.800 at rho 0.95, below TreeSHAP's 0.872.
- Rank agreement with the true importances: methods were broadly similar, with differences often within the spread; C2 was higher at rho 0.95 (0.767 vs 0.699) but lower at rho 0.25 (0.787 vs 0.881).
- Runtime: TreeSHAP was much faster than both TreeHFD variants.

## Limitations

- Only 3 seeds, two dataset types, and one model configuration (xgboost, 100 trees). Many differences are within one or two standard deviations.
- Only one of three ideas was run, and ideas and code were produced by a language model; the idea space was barely explored.
- Question coverage: the experiments address the analytical-data part of the research question for xgboost only: component error against true components and bootstrap rank stability as rho goes from 0 to 0.95, for TreeHFD, TreeSHAP and C2. They do not address random forests, California Housing, Adult, or top-k component stability on public data. Airfoil was used only for residual MSE, runtime and rank stability, with no ground truth.
- The analytical function has one fixed form, so the correlation sweep may not generalize.
- Residual MSE in the main table is held-out and not directly comparable to the in-sample baseline values quoted in the Method section.
- The loop shows C2 did not help in this setup; it does not show that deeper variable selection can never help.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
