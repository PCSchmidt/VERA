## Literature review

None of the supplied passages evaluates credal ambiguity sets (imprecise Dirichlet or epsilon-contamination neighborhoods) against Wasserstein or moment-based sets, so the central comparison cannot be answered from this evidence. The evidence is mainly about Wasserstein sets, with some material on moment-based sets.

In a portfolio experiment, the same source reports that out-of-sample performance first improves and then deteriorates as the radius grows [R7]. It also reports how the reliability of the cost guarantee behaves in the radius [R7]. A control-setting study reports that out-of-sample cost does not decrease monotonically with the Wasserstein radius, and that an optimal radius exists (e.g., 0.02 for N = 20) [R37]. The same study reports that reliability rises with both radius and sample size [R37].

On calibration, the portfolio study says it calibrates the size of the moment-type LCX ambiguity set by bootstrapping so as to guarantee a desired reliability level 1 - β [R7]. That study reports an advantage for Wasserstein solutions over the SAA and LCX solutions [R7]. A high-dimensional regression study finds that a theory-based radius choice matches cross-validation [R5].

For moment-based sets, one source describes a tractability advantage over Wasserstein sets [R7]. Another study of a moment-and-distribution model, built on a confidence region for the mean and covariance, reports that in a portfolio example its framework gives better-performing policies on the true distribution of daily returns [R66].

What is not established: any head-to-head comparison of credal, Wasserstein and moment sets under the same tuning rule; results across n from about 10 to 200 combined with contamination of 0 to 20%; and the behavior of guarantee reliability under contamination for any of the three families.

## Retrieval and its limits

This review rests on 5 search queries, which retrieved 100 candidate papers. A relevance screen kept 32 and set aside 68; 6 were read in full text and 26 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R5] Liviu Aolaritei, Soroosh Shafiee, Florian Dörfler. Wasserstein Distributionally Robust Estimation in High Dimensions: Performance Analysis and Optimal Hyperparameter Tuning. 2022. arXiv:2206.13269. https://arxiv.org/abs/2206.13269
[R7] Peyman Mohajerin Esfahani, Daniel Kühn. Data-Driven Distributionally Robust Optimization Using the Wasserstein Metric: Performance Guarantees and Tractable Reformulations. 2015. arXiv:1505.05116. https://arxiv.org/abs/1505.05116
[R37] Insoon Yang. Wasserstein Distributionally Robust Stochastic Control: A Data-Driven Approach. 2020. doi:10.1109/tac.2020.3030884. https://doi.org/10.1109/tac.2020.3030884
[R66] Erick Delage, Yinyu Ye. Distributionally Robust Optimization Under Moment Uncertainty with Application to Data-Driven Problems. 2010. doi:10.1287/opre.1090.0741. https://doi.org/10.1287/opre.1090.0741
