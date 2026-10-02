## Literature review

The central source, the TreeHFD paper, frames the problem as one of dependence: the Hoeffding decomposition is unique only for independent inputs, and under dependence it is generalized through hierarchical orthogonality constraints [R5]. A related review notes that mutual orthogonality is a consequence of independence and so generally fails under realistic correlations [R10]. Another source describes the generalized decomposition as existing and unique under bounded-density assumptions, but its geometry as still implicit [R35].

On accuracy, TreeHFD's own experiments show it approximates the decomposition of fitted xgboost models well on real data [R5]. The same paper reports that TreeHFD's main effects and interactions are nearly hierarchically orthogonal, whereas TreeSHAP's are often entangled [R999]. On California Housing, it reports that TreeHFD identifies the San Francisco Bay Area peak in the Longitude component, which TreeSHAP does not really detect [R5]. For random forests, the authors report lower accuracy than with xgboost on the sinusoidal main effect and on the interaction components in an analytical case [R5]. These are orthogonality and residual measures on fitted models, not errors against ground-truth components across a correlation sweep from 0 to 0.95.

Other sources suggest TreeSHAP and HFD-style methods often agree in global rankings. One reports very close top-10 rankings across six datasets [R10]. Another reports mean rank correlations of about 0.91 to 0.93 with SHAP explainers, with a lowest value of 0.7619 against TreeSHAP [R35]. This agreement contrasts with TreeHFD's finding that TreeSHAP decompositions are noisy and entangled, so the sources differ on how closely the two methods align at the component level.

Evidence on TreeSHAP under correlation is partial. One construction shows exact TreeSHAP giving strikingly unequal importance to statistically interchangeable redundant channels [R6]. A neural-network study with synthetic data of increasing correlation found that correlation may dramatically increase the variance of the derived attributions [R41]. That study concerns neural networks and not tree ensembles, so it only motivates the bootstrap-stability question.

Limits on TreeHFD itself are noted elsewhere: a later paper says it is computationally limited to shallow trees and assumes non-empty leaves [R15]. TreeHFD also inherits any overfitting of the underlying ensemble [R5].

What is not established by these passages: no source measures TreeHFD or TreeSHAP error against known components as correlation rises from 0 to 0.95, and none reports bootstrap-refit rank stability of component importances for random forests or boosted ensembles. The Adult dataset is not used for TreeHFD in the supplied passages, and no top-k component stability is reported for California Housing. Whether TreeHFD's advantage persists at very high correlation, where estimation in sparse regions is hard, is therefore untested here.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
