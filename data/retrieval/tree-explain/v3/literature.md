## Literature review

The sources do not answer the research question directly: none of them reports error against ground truth, or bootstrap rank stability, as pairwise feature correlation rho rises from 0 to 0.95. What they do establish concerns the TreeHFD method and its relation to TreeSHAP.

The TreeHFD paper presents the algorithm as an estimator of the Hoeffding decomposition of a tree ensemble from a data sample, aimed at dependent inputs [R5]. The theory it rests on is the generalization of the decomposition through hierarchical orthogonality constraints, which gives unique and sparse decompositions [R5]. A companion theoretical paper notes that for dependent inputs the components are only hierarchically orthogonal, so the usual conditional-expectation formula no longer isolates pure interactions [R35].

On real data, the TreeHFD authors report that the residual MSE of TreeHFD is about 1% of the output variance across their tested datasets [R5]. They also report that the maximum absolute correlation between interactions and main effects is about 0.05 or smaller for TreeHFD, while it is frequently above 0.5 for TreeSHAP [R5]. On California Housing, the same paper says the TreeSHAP decomposition is noisy and that its Longitude main effect is entangled with the Longitude-Latitude interaction [R5]. A related claim of instability is that a slight input perturbation may change TreeSHAP's decomposition values a lot, although this concerns local values under input perturbation, not bootstrap refits [R5].

For random forests, the TreeHFD paper itself reports lower accuracy than with xgboost on an analytical case, for a sinusoidal main effect and for interactions [R5]. This bears on the planned comparison of random forests and gradient-boosted ensembles, but that analytical case is not described in these passages as a controlled sweep over correlation.

The sources also disagree about how far TreeSHAP and the functional decomposition diverge. The TreeHFD authors state that TreeSHAP is strongly connected to the Hoeffding decomposition [R5]. A later paper comparing a different estimator with SHAP reports mean Spearman rank correlations of feature importance of 0.9130 to 0.9343, with a low of 0.7619 for TreeSHAP on one dataset [R35]. Global importance rankings may therefore agree between the methods even where individual components differ, though these passages do not test this under rising correlation.

Limits of TreeHFD are noted elsewhere: one paper says it is computationally limited to shallow trees and assumes non-empty leaves [R15]. The same group notes that in high-dimensional sparse datasets high feature correlations pose challenges for standard Shapley-value estimators [R15]. Earlier work on purification gives an exact algorithm for piecewise-constant models, but it requires the data density [R15].

Not established by these passages: error against ground-truth components at rho from 0 to 0.95, bootstrap rank stability of component importances for either TreeHFD or TreeSHAP, and stability of top-k components on California Housing or Adult. The real-data evidence reports orthogonality and residual error without ground truth, so it cannot show recovery accuracy, and the TreeHFD authors acknowledge that the method inherits any overfitting of the initial ensemble [R5].

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
