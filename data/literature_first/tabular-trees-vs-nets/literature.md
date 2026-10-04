## Literature review

The sources do not directly answer the question as posed, because none of them subsamples public tabular classification datasets from a few hundred to a few tens of thousands of rows and compares GBDTs with small tuned MLPs under an equal CPU search budget. The closest evidence comes from a slicing study, a benchmark at medium sizes, and several indirect comparisons.

The most relevant source reports a dataset slicing protocol running from N=100 to N=15,000 rows [R29]. It finds that models are indistinguishable at small scales [R29]. It adds that a gradient-boosted tree advantage emerges as sample sizes grow [R29]. The abstract does not say that this comparison involved tuned MLPs specifically or an equal search budget, so this evidence is only suggestive for the question.

A large benchmark that accounts for hyperparameter search reports that tree-based models remain state-of-the-art on medium-sized data (about 10K samples), even without accounting for their superior speed [R33]. The same work notes that the gap stays wide across random-search budgets [R33]. It also cautions that this might change with added regularization [R33].

Work on regularization cocktails disagrees with the tree-favoring picture. It also reports that this advantage grows with tuning time [R8]. These results are not broken down by training-set size, so they do not locate a crossover.

A later TabPFN version is described as a tabular foundation model that outperforms all previous methods on datasets with up to 10,000 samples by a wide margin [R66]. These comparisons use GPUs or different methods, so they do not address a CPU-only equal-budget MLP comparison.

Statements that deep learning trails GBDTs on small data are reported secondhand. TabPFN's authors note that earlier work found deep learning baselines do not outperform or match GBDTs for small to medium-sized data [R1]. HyperTab, a small-data neural method, states that it is especially challenging to surpass tree-like ensembles such as XGBoost or Random Forests on small datasets (under 1k samples) [R49].

What is not established: a size at which the gap closes or reverses for tuned MLPs, results under an equal CPU search budget at each subsample size, and a consistent direction of the gap across sizes. Existing sources either do not vary size or do not isolate small tuned MLPs.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 32 and set aside 88; 6 were read in full text and 26 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R1] Noah Hollmann, Müller, Samuel, Katharina Eggensperger et al.. TabPFN: A Transformer That Solves Small Tabular Classification Problems in a Second. 2022. arXiv:2207.01848. https://arxiv.org/abs/2207.01848
[R8] Arlind Kadra, Marius Lindauer, Frank Hutter et al.. Well-tuned Simple Nets Excel on Tabular Datasets. 2021. arXiv:2106.11189. https://arxiv.org/abs/2106.11189
[R29] Hieu  Trung Nguyen. The Small-Sample Illusion: How Data Quantity, Not Quality, Drives Machine Learning Performance on Tabular Data. 2026. doi:10.2139/ssrn.6798854. https://doi.org/10.2139/ssrn.6798854
[R33] Léo Grinsztajn, Edouard Oyallon, Gaël Varoquaux. Why do tree-based models still outperform deep learning on tabular data?. 2022. arXiv:2207.08815. https://arxiv.org/abs/2207.08815
[R49] Witold Wydmański, Oleksii Bulenok, Marek Śmieja. HyperTab: Hypernetwork Approach for Deep Learning on Small Tabular Datasets. 2023. doi:10.48550/arxiv.2304.03543. https://doi.org/10.48550/arxiv.2304.03543
[R66] Noah Hollmann, Samuel Müller, Lennart Purucker et al.. Accurate predictions on small data with a tabular foundation model. 2025. doi:10.1038/s41586-024-08328-6. https://doi.org/10.1038/s41586-024-08328-6
