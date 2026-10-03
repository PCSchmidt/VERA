## Literature review

The TreeHFD paper introduces an algorithm to estimate the Hoeffding decomposition of a tree ensemble from a data sample [R5]. Other work notes that mutual orthogonality generally fails under realistic correlations [R10].

On California Housing, the TreeHFD authors report that TreeSHAP is noisy and that its Longitude main effect is entangled with the Longitude-Latitude interaction [R5]. They also report that TreeSHAP is sensitive to small input perturbations [R5].

A further study reports that the lowest rank correlation with TreeSHAP was 0.7619, obtained on the BS dataset [R35]. These agreement results do not isolate the effect of increasing correlation.

Evidence on TreeSHAP under redundancy is less favourable: a counterexample shows exact TreeSHAP giving very unequal importance to interchangeable redundant channels [R6]. In neural networks, correlation has been shown to increase variance of attributions, using synthetic data with known ground truth [R41].

TreeHFD accuracy depends on the ensemble: with random forests it was less accurate than with xgboost for a sinusoidal main effect and for interaction components [R5]. Another paper notes that TreeHFD is computationally limited to shallow trees and assumes non-empty leaves [R15].

What is not established: none of the passages reports component error against ground truth for TreeHFD as pairwise correlation rises from 0 to 0.95, nor bootstrap rank stability of component importances across refit random forests and boosted ensembles. The real-data comparisons also measure orthogonality and agreement rather than bootstrap stability of top-k components, and no ground truth exists there.

## Retrieval and its limits

This review rests on 5 search queries, which retrieved 100 candidate papers. A relevance screen kept 31 and set aside 69; 6 were read in full text and 25 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R5] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R6] Chiemere Victor Ezeokechukwu, Funmilayo  Abibat Sanusi. A Counterexample to Symmetric Feature Attribution in TreeSHAP: Unequal Credit Assignment Among Redundant Risk Reporting Channels. 2026. doi:10.2139/ssrn.7354454. https://doi.org/10.2139/ssrn.7354454
[R10] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R15] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Exact Functional ANOVA Decomposition for Categorical Inputs Models. 2026. arXiv:2603.02673. https://arxiv.org/abs/2603.02673
[R35] Baptiste Ferrere, Nicolas Bousquet, Fabrice Gamboa et al.. Generalized Functional ANOVA: A Complete Theoretical Framework. 2026. arXiv:2605.18422. https://arxiv.org/abs/2605.18422
[R41] Evan Krell, Antonios Mamalakis, Scott A. King et al.. The influence of correlated features on neural network attribution methods in geoscience. 2025. doi:10.1017/eds.2025.19. https://doi.org/10.1017/eds.2025.19
