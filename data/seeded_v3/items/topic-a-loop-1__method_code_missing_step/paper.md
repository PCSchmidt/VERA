## Abstract

We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions. A language-model-driven research loop produced 3 ideas and ran 2 of them on a small subset: two datasets (Analytical, Airfoil), 3 seeds, xgboost with 100 trees, held-out data. The baseline reproduced the paper's reference values within the registered tolerance. No idea beat the baseline on every dataset. This is a negative result.

## Related work

TreeHFD frames the problem as one of dependence. The Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. Mutual orthogonality follows from independence and so generally fails under realistic correlations [R10]. The generalized decomposition exists and is unique under bounded-density assumptions, but its geometry is still implicit [R35].

On accuracy, TreeHFD's own experiments show it approximates the decomposition of fitted xgboost models well on real data. Its main effects and interactions are nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R5]. For random forests, its authors report lower accuracy than with xgboost on the sinusoidal main effect and on interaction components in an analytical case [R5]. Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings [R10][R35], which contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled.

Evidence on TreeSHAP under correlation is partial. One construction shows exact TreeSHAP giving unequal importance to interchangeable redundant channels [R6]. A neural-network study found that correlation may dramatically increase the variance of attributions [R41]. TreeHFD is computationally limited to shallow trees and assumes non-empty leaves [R15], and it inherits any overfitting of the underlying ensemble [R5]. The ensemble used here is xgboost [R101].

## Method

The baseline is TreeHFD with default settings. Metric: residual MSE (%), lower is better, on held-out data; runtime in seconds is also reported. Baseline residual MSE in-sample, the paper's convention, is 0.570 (Analytical) and 1.52 (Airfoil); the table shows held-out values, which are higher.

Two ideas were run:

- **C1, interaction screening by importance.** Fit TreeHFD with interaction_order=1 for main effects. The depth parameter is chosen by five-fold cross-validation on the training rows. Rank variable pairs by co-occurrence on tree paths, or by variance of the residual explained by a pair. Pass only the top-k pairs as interaction_list, with k chosen on a validation split.
- **C3, component-wise ridge recalibration.** Predict the components on a held-out calibration set. Regress the model's predictions on an intercept plus all components with non-negative ridge regression. Apply the learned scalar weights to each component on test data.

A third idea was generated but not run.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 28.0 ± 0.24 | 4.73 ± 0.11 | 3.35 ± 0.20 |
| C1: Interaction screening by importance | 2.55 ± 0.32 | 48.1 ± 1.9 | 6.07 ± 1.1 | 12.3 ± 0.76 |
| C3: Component-wise ridge recalibration | 2.93 ± 0.34 | 29.2 ± 0.42 | 559431188 ± 25709741 | 3.91 ± 0.12 |

The baseline reproduction gate passed. C1 lowered Analytical residual MSE (2.55 ± 0.32 vs 2.79 ± 0.32), but the difference is within one standard deviation across 3 seeds. C1 was worse on Airfoil (6.07 ± 1.1 vs 4.73 ± 0.11) and slower on both datasets (48.1 s vs 28.0 s; 12.3 s vs 3.35 s), contrary to the idea's runtime motivation. C3 was slightly worse on Analytical (2.93 ± 0.34) and failed badly on Airfoil (559431188 ± 25709741), which indicates a numerical or implementation failure that we did not diagnose. No idea beat the baseline on every dataset.

## Limitations

- Only 3 seeds, two datasets, and one model configuration (xgboost, 100 trees).
- The ideas were produced and implemented by a language model; implementation bugs, especially in C3 on Airfoil, are possible and were not investigated. The C3 result may not reflect the idea itself.
- Only 2 of 3 ideas were run, with no tuning reported beyond what each idea specified.
- The Analytical gain for C1 is not distinguishable from noise.
- Relation to the broader research question (correlated features, TreeHFD versus TreeSHAP): these experiments address almost none of it. They measure residual MSE and runtime of TreeHFD variants on Analytical and Airfoil. They do not vary pairwise correlation from 0 to 0.95, do not compare against TreeSHAP, do not measure error against ground-truth components, do not test bootstrap rank stability, do not use random forests or gradient-boosted ensembles beyond xgboost, and do not use California Housing or Adult. Nothing here speaks to whether TreeHFD stays accurate or stable under correlation.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
[R101] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
