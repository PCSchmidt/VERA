## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A crude automated loop generated 3 ideas and ran 2 of them on a small subset of problems. The baseline reproduced the paper's reference values within the registered tolerance. No idea beat the baseline on every dataset. This is a negative result. One idea (a shallow depth_variable sweep) lowered held-out residual MSE on three of four datasets and raised it on Airfoil. The other idea (ridge recalibration) was slightly worse than the baseline on all four datasets.

## Related work

TreeHFD frames the problem as one of dependence. The Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. Another source describes the generalized decomposition as existing and unique under bounded-density assumptions, with its geometry still implicit [R35].

On accuracy, TreeHFD's own experiments show it approximates the decomposition of fitted xgboost models well on real data. The same paper reports that its components are nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R5]. For random forests, it reports lower accuracy than for xgboost in an analytical case [R5].

Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10], [R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled. Evidence on TreeSHAP under correlation is partial: one construction shows unequal importance given to interchangeable redundant channels [R6]. A neural-network study found that correlation may dramatically increase attribution variance [R41].

TreeHFD is computationally limited to shallow trees and assumes non-empty leaves [R15]. It also inherits any overfitting of the underlying ensemble [R5]. No source measures error against known components across a correlation sweep, or bootstrap rank stability for tree ensembles.

## Method

Baseline: TreeHFD fitted to an xgboost model [R101] with 100 trees. Datasets: Analytical, Analytical rho0 (independent inputs, pairwise correlation 0, same function, noise, n = 5000 and model as Analytical), Analytical rho95 (pairwise correlation 0.95 between all six Gaussian inputs, otherwise the same), and Airfoil. We use 3 seeds, held-out data, and the metric residual MSE (%), lower is better. Runtime is also reported.

The baseline reproduced the paper's reference values within tolerance (gate verdict True). The paper's convention is in-sample residual MSE: 0.570 (Analytical), 0.792 (rho0), 0.126 (rho95) and 1.52 (Airfoil). The table below reports held-out values, which are higher.

Ideas tried:
- **C3, residual ridge recalibration.** On training data, compute model predictions and TreeHFD components. Fit a non-negative ridge regression with intercept of the predictions on the component columns. Apply the learned per-component scales to held-out components. Each component still depends only on its own variables. The aim was to correct shrinkage bias, which matters most under correlation.
- **C1, shallow depth_variable sweep.** Fit TreeHFD with depth_variable in several values (e.g. 2, 3, 4, 6, None). Pick the value with the lowest residual MSE on a held-out split of the training data, then refit and predict. Shallower variable selection cuts runtime, and tuning it can lower residual error.

A third idea was generated but not run.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Analytical rho0 · Residual MSE (%) ↓ | Analytical rho0 · Runtime (s) ↓ | Analytical rho95 · Residual MSE (%) ↓ | Analytical rho95 · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.7 ± 0.58 | 5.54 ± 0.40 | 30.1 ± 1.2 | 1.03 ± 0.022 | 22.0 ± 0.42 | 4.73 ± 0.11 | 3.23 ± 0.13 |
| C3: Residual ridge recalibration | 2.85 ± 0.33 | 33.3 ± 0.11 | 5.69 ± 0.37 | 34.7 ± 1.1 | 1.04 ± 0.037 | 24.9 ± 0.43 | 4.88 ± 0.17 | 3.82 ± 0.19 |
| C1: Shallow depth_variable sweep | 2.41 ± 0.16 | 22.1 ± 0.38 | 4.37 ± 0.52 | 16.7 ± 4.1 | 0.712 ± 0.044 | 20.1 ± 0.11 | 5.09 ± 0.18 | 6.60 ± 0.11 |

No idea beat the baseline on every dataset.

C3 was not better on any dataset. Its residual MSE was marginally higher than the baseline on all four (for example 2.85 vs 2.79 on Analytical), well within the seed spread, and its runtime was higher everywhere. It gave no evidence of helping, including under correlation (rho95: 1.04 vs 1.03).

C1 lowered residual MSE on Analytical (2.79 vs 2.79), rho0 (4.37 vs 5.54) and rho95 (0.712 vs 1.03), and lowered runtime on those three. On Airfoil it was worse in error (5.09 vs 4.73) and in runtime (6.60 s vs 3.23 s). Given the 3 seeds, the Analytical gain is modest relative to the spread (±0.32 baseline, ±0.16 for C1); the rho0 and rho95 gains look larger relative to the spread, but we ran no significance test.

So C1 is a promising but mixed result, not a general improvement.

## Limitations

- Only 3 seeds, so standard deviations are rough and no formal tests were run.
- Four datasets, of which three are variants of one analytical function; only one is real (Airfoil).
- One model configuration (xgboost, 100 trees).
- Ideas were produced and implemented by a language model in a crude loop; implementation bugs cannot be ruled out. Only 2 of 3 ideas were run.
- The tables report held-out values, while the reproduction gate used the paper's in-sample convention; the two are not directly comparable.
- C1's depth choice used a split of the training data, and we did not examine which depth values were selected.

Relation to the research question: the experiments touch only a narrow part of it. The Analytical rho0 and rho95 datasets give two points on the correlation axis (0 and 0.95), but not a sweep, and the metric is residual MSE of the decomposition against the fitted model's predictions. They do not measure error against ground-truth main effects and interactions, so (a) is not addressed. They do not compare with TreeSHAP-style attributions. They do not measure rank stability of component importances across bootstrap refits, or use random forests or other boosted ensembles, so (b) is not addressed. No public datasets such as California housing or Adult were used, and Airfoil was not used for bootstrap stability. The results say only that, in this setup, residual MSE changed with a depth setting; they say nothing about whether TreeHFD stays accurate and stable under correlation relative to alternatives.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
