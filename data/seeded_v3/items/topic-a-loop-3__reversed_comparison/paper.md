## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A language-model-driven loop generated 3 ideas and ran 2 of them on a subset of the benchmark. The baseline reproduced the paper's reference values within the registered tolerance (gate verdict True). Neither idea beat the baseline on any dataset, so this is a negative result. The loop only established that these two post-hoc corrections do not help here, within a narrow setup.

## Related work

TreeHFD frames the problem as one of dependence: the Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. Another source describes the generalized decomposition as existing and unique under bounded-density assumptions, with its geometry still implicit [R35].

TreeHFD's own experiments show that it approximates the decomposition of fitted xgboost models well on real data. They also report that its components are nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R5]. For random forests, the authors report lower accuracy than with xgboost in an analytical case [R5]. Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10][R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled.

Evidence on TreeSHAP under correlation is partial. One construction shows unequal importance given to interchangeable redundant channels [R6]. A neural-network study found that correlation may greatly increase attribution variance [R41]. TreeHFD is limited to shallow trees and assumes non-empty leaves [R15], and it inherits any overfitting of the underlying ensemble [R5]. The xgboost model itself is described in [R101].

No source measures TreeHFD or TreeSHAP error against known components across a correlation sweep, or reports bootstrap rank stability of component importances.

## Method

Setup: xgboost with 100 trees, 3 seeds, held-out data. The metric is residual MSE (%) (lower is better), plus runtime. Datasets:
- Analytical.
- Uncorrelated: the analytical function with independent inputs (pairwise correlation 0), same noise, n = 5000 and model.
- Correlated95: the analytical function with pairwise correlation 0.95 between all six Gaussian inputs, same noise, n = 5000 and model.
- Airfoil.

Baseline residual MSE (%) in-sample, the paper's convention, was: Analytical 0.570; Uncorrelated 0.792; Correlated95 0.126; Airfoil 1.52. The table reports held-out values, which are higher.

Two of three generated ideas were run:
- **C3, residual spline main effects:** take the residual (model prediction minus current component sum) on training data. For each variable, and each selected variable pair, fit a low-order spline or binned smoother (2D binned smoother or tensor spline for pairs) on that residual. Add the corrections to the matching components and evaluate on held-out data.
- **C2, residual refit on components:** after fitting TreeHFD, fit a ridge regression of the model predictions on the stacked component columns to get per-component scalar weights and an intercept. Apply these on test data. Each component still depends only on its own variables.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = higher is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Uncorrelated · Residual MSE (%) ↓ | Uncorrelated · Runtime (s) ↓ | Correlated95 · Residual MSE (%) ↓ | Correlated95 · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 29.8 ± 0.65 | 5.54 ± 0.40 | 31.0 ± 0.69 | 1.03 ± 0.022 | 21.3 ± 0.25 | 4.73 ± 0.11 | 3.26 ± 0.054 |
| C3: Residual spline main effects | 2.81 ± 0.33 | 32.1 ± 0.54 | 5.58 ± 0.41 | 33.8 ± 0.79 | 1.03 ± 0.017 | 25.9 ± 0.46 | 4.76 ± 0.13 | 3.86 ± 0.097 |
| C2: Residual refit on components | 2.92 ± 0.34 | 33.1 ± 0.13 | 5.79 ± 0.36 | 35.0 ± 0.93 | 1.09 ± 0.043 | 25.8 ± 0.16 | 4.88 ± 0.17 | 3.96 ± 0.10 |

No idea beat the baseline on every dataset; in fact, on residual MSE neither was better on any dataset. C3 was essentially tied with the baseline: for example 2.81 ± 0.33 vs 2.79 ± 0.32 on Analytical, and 1.03 on Correlated95 for both, with differences far inside the seed spread. C2 was slightly worse on all four datasets (for example 5.79 ± 0.36 vs 5.54 ± 0.40 on Uncorrelated, and 1.09 vs 1.03 on Correlated95), though these gaps are also comparable to the standard deviations. Both ideas cost more runtime than the baseline on every dataset (for example 33.1 s vs 29.8 s on Analytical for C2).

## Limitations

- Only 3 seeds; differences of a few hundredths to tenths of a percent are within noise, so we cannot rank C3 against the baseline, only say it showed no gain.
- One model configuration (xgboost, 100 trees) and four datasets, three of them synthetic variants of one function.
- Ideas were produced and implemented by a language model, with only 2 of 3 run, so the search was small and the implementations may be imperfect.
- Held-out numbers differ from the paper's in-sample convention, so they are not directly comparable to the paper's values.
- Relation to the literature research question: the Uncorrelated and Correlated95 datasets give two correlation levels (0 and 0.95), not a sweep. The metric is residual MSE of the component sum against the model, not error against ground-truth components. These experiments do not address TreeSHAP comparisons, bootstrap rank stability of component importances, random forests or other boosted ensembles, or public datasets such as California housing or Adult. Airfoil has no known true components. They bear on the question only by showing that two post-hoc corrections do not reduce residual error at either correlation level.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
