## Literature review

The sources do not offer a direct measurement of the gap between boosted trees and tuned small MLPs across subsampled sizes under an equal CPU search budget. The closest evidence is a slicing study that ran from 100 to 15,000 rows [R29]. The Small-Sample Illusion study reports that models perform indistinguishably at small scales and that a distinct gradient-boosted tree advantage emerges as sample sizes increase [R29]. The estimation study comparing tree ensembles and deep learning reports that deep neural networks achieve the minimal MSE when facing strong nonlinearity with moderate or large sample sizes [R29]. The abstract does not say that its models were tuned MLPs or that search budgets were equal, so it is not a clean answer.

Benchmark studies agree that trees lead at medium sizes. Grinsztajn and colleagues report that tree-based models stay state-of-the-art at about 10K samples, even without counting their speed advantage [R33]. Grinsztajn and colleagues report that tree-based models are superior for every random search budget, and the performance gap stays wide even after a large number of random search iterations [R33].

Some evidence points the other way for tuned MLPs. In Kadra and colleagues' study, regularization cocktails for MLPs were statistically significantly better than XGBoost after 30 minutes of HPO time [R8]. Grinsztajn and colleagues caution that the datasets in that paper differ from theirs, including game-inspired deterministic ones where the method does very well [R33]. The Kadra results are not stratified by training-set size in the supplied passages.

At small sizes, the strongest reported challenger is a pretrained model rather than a tuned MLP. TabPFN is reported to clearly outperform boosted trees on datasets with up to 1,000 training points [R1]. TabPFN is reported to outperform all previous methods on datasets with up to 10,000 samples by a wide margin, using substantially less training time [R66]. These results compare TabPFN with trees and do not isolate small tuned MLPs.

A few sources speak to the cost side on CPU. One study on a CPU without GPU reports that tree ensembles trained in 0.1-0.2 seconds against 0.6-0.7 seconds for a DNN at n = 500 [R6]. That study used default tree settings and fixed network configurations rather than an equal search budget. The same abstract names a stabilisation point of 2,500 rows [R6].

What is not established is whether a crossover size exists for small tuned MLPs against XGBoost or LightGBM under matched CPU search budgets. The sources point in different directions, with the gap reported as indistinguishable at small sizes, as wide near 10K rows, and as reversed in some tuned-MLP work, and the supplied passages do not reconcile these under one protocol.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 160 candidate papers. A relevance screen kept 32 and set aside 128; 6 were read in full text and 26 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R1] Noah Hollmann, Müller, Samuel, Katharina Eggensperger et al.. TabPFN: A Transformer That Solves Small Tabular Classification Problems in a Second. 2022. arXiv:2207.01848. https://arxiv.org/abs/2207.01848
[R6] Yaoping Wang. Machine Learning for Estimation: Comparing Tree Ensembles and Deep Learning on Tabular Data. 2026. doi:10.54254/2755-2721/2026.gf34864. https://doi.org/10.54254/2755-2721/2026.gf34864
[R8] Arlind Kadra, Marius Lindauer, Frank Hutter et al.. Well-tuned Simple Nets Excel on Tabular Datasets. 2021. arXiv:2106.11189. https://arxiv.org/abs/2106.11189
[R29] Hieu  Trung Nguyen. The Small-Sample Illusion: How Data Quantity, Not Quality, Drives Machine Learning Performance on Tabular Data. 2026. doi:10.2139/ssrn.6798854. https://doi.org/10.2139/ssrn.6798854
[R33] Léo Grinsztajn, Edouard Oyallon, Gaël Varoquaux. Why do tree-based models still outperform deep learning on tabular data?. 2022. arXiv:2207.08815. https://arxiv.org/abs/2207.08815
[R66] Noah Hollmann, Samuel Müller, Lennart Purucker et al.. Accurate predictions on small data with a tabular foundation model. 2025. doi:10.1038/s41586-024-08328-6. https://doi.org/10.1038/s41586-024-08328-6
