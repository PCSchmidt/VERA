## Literature review

The supplied passages contain no study that compares credal sets (imprecise Dirichlet or epsilon-contamination neighborhoods) with Wasserstein and mean-covariance sets in small, contaminated samples under a common tuning rule. The Wasserstein literature does supply some relevant evidence on reliability and radius tuning. Mohajerin Esfahani and Kuhn's paper states that the optimal value of the Wasserstein distributionally robust problem provides an upper confidence bound on the achievable out-of-sample cost [R4]. In their portfolio experiments, the reliability of the cost certificate did not decrease as the radius grew [R4].

Wasserstein guarantees are known to degrade with dimension. Gao and coauthors report that the radius rule in the original guarantee suffers from the curse of dimensionality because the radius shrinks too slowly even for problems in moderate dimensions [R5]. The same authors note that radius selection is often achieved via cross validation in practice [R5].

One passage compares Wasserstein and moment sets directly, but only for chance-constrained problems with larger samples. In a hydro planning comparison of a Wasserstein and a moment-based chance-constrained model, with training sizes N in {500, 700, 900, 1000}, 'We observe that the out-of-sample reliability of both models exceed the target reliability of 90%, but that of the Wasserstein (P-CC) is significantly closer to the target level than that of the moment (P-CC).' [R8]. That comparison used N from 500 to 1000 and a chance-constrained problem, so it does not cover the small samples of interest here.

Contamination is addressed only within Wasserstein-type frameworks. Outlier-robust Wasserstein DRO adds total-variation contamination that allows an epsilon-fraction of data to be arbitrarily corrupted [R22]. This is not a comparison against credal sets or moment sets under matched tuning. Not established by these passages: the relative out-of-sample cost and guarantee reliability of imprecise Dirichlet or epsilon-contamination sets, Wasserstein balls and mean-covariance sets for n from 10 to 200 and contamination from 0 to 20%.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 65 and set aside 55; 6 were read in full text and 59 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R4] Peyman Mohajerin Esfahani, Daniel Kühn. Data-Driven Distributionally Robust Optimization Using the Wasserstein Metric: Performance Guarantees and Tractable Reformulations. 2015. arXiv:1505.05116. https://arxiv.org/abs/1505.05116
[R5] Gao, Rui. Finite-Sample Guarantees for Wasserstein Distributionally Robust Optimization: Breaking the Curse of Dimensionality. 2020. arXiv:2009.04382. https://arxiv.org/abs/2009.04382
[R8] Haoming Shen, Ruiwei Jiang. Convex Chance-Constrained Programs with Wasserstein Ambiguity. 2021. arXiv:2111.02486. https://arxiv.org/abs/2111.02486
[R22] Sloan Nietert, Ziv Goldfeld, Soroosh Shafieezadeh-Abadeh. Outlier-Robust Wasserstein DRO. 2023. arXiv:2311.05573. https://arxiv.org/abs/2311.05573
