## Literature review

The sources establish what TreeHFD is meant to do, but none of them reports the experiment the question describes. The TreeHFD paper states that the Hoeffding decomposition breaks black-box models into a unique sum of lower-dimensional functions, provided that input variables are independent [R32]. The TreeHFD authors state that, for dependent inputs, the decomposition is generalized through hierarchical orthogonality constraints [R32]. The TreeHFD authors report that TreeHFD was shown to perform well in experiments on simulated and real data [R32].

On the relation to TreeSHAP, the TreeHFD abstract reports an empirical finding of a strong connection [R32]. The Fourier-analysis paper observes that a similar alignment between SHAP attributions and its HFD-like decomposition persists on several real-world datasets exhibiting substantial feature dependence [R5].

Other sources bear on why correlation might matter for attribution accuracy and rank stability. The conditional permutation importance paper reports that random forest variable importance measures are biased toward correlated predictors [R11]. The Kernel SHAP extension paper states that Shapley values suffer from the inclusion of unrealistic data instances when features are correlated, so explanations may be misleading [R19]. The generalized ANOVA paper for dependent measures reports that the correlation structure of random variables can significantly alter the composition of component functions and produce distinct rankings [R35]. A study of path-dependent TreeSHAP shows two decision trees computing the same function can yield different feature rankings [R88]. The XAI-Bench paper offers synthetic datasets that allow ground-truth Shapley values to be computed for benchmarking attribution methods [R59].

The evidence leaves the central question unanswered. None of the passages reports component-level error against known main effects and a known pairwise interaction as the correlation rho rises from 0 to 0.95. None reports bootstrap-refit rank stability for random forests or gradient-boosted ensembles under increasing correlation. The agreement with TreeSHAP reported above is a similarity between methods and is not a comparison against ground truth, so it does not show which method is more accurate. The passages also give no bootstrap stability results for top-k components on California housing or Adult.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 37 and set aside 83; 6 were read in full text and 31 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R5] Baptiste Ferrere, Nicolás Bousquet, Fabrice Gamboa et al.. Fourier Analysis on the Boolean Hypercube via Hoeffding Functional Decomposition. 2025. doi:10.48550/arxiv.2510.07088. https://doi.org/10.48550/arxiv.2510.07088
[R11] Carolin Strobl, Anne‐Laure Boulesteix, Thomas Kneib et al.. Conditional variable importance for random forests. 2008. doi:10.1186/1471-2105-9-307. https://doi.org/10.1186/1471-2105-9-307
[R19] Kjersti Aas, Martin Jullum, Anders Løland. Explaining individual predictions when features are dependent: More accurate approximations to Shapley values. 2021. doi:10.1016/j.artint.2021.103502. https://doi.org/10.1016/j.artint.2021.103502
[R32] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R35] Sharif Rahman. A Generalized ANOVA Dimensional Decomposition for Dependent Probability Measures. 2014. arXiv:1408.0722. https://arxiv.org/abs/1408.0722
[R59] Yang Liu, Sujay Khandagale, Colin White et al.. Synthetic Benchmarks for Scientific Research in Explainable Machine Learning. 2021. doi:10.48550/arxiv.2106.12543. https://doi.org/10.48550/arxiv.2106.12543
[R88] Khashayar Filom, Alexey Miroshnikov, Konstandinos Kotsiopoulos et al.. On marginal feature attributions of tree-based models. 2024. arXiv:2302.08434. https://arxiv.org/abs/2302.08434
