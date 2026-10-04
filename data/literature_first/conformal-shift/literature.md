## Literature review

Weighted conformal prediction for covariate shift is described as covering the case where the likelihood ratio is known [R2]. The original paper states the method gives distribution-free intervals when the likelihood ratio is known or can be estimated accurately from unlabeled test covariates [R29]. One secondary source reports a marginal guarantee of at least 1 minus alpha under covariate shift when the ratios are exactly known [R4]. The same source says that with estimated ratios, coverage degrades at a rate controlled by estimation error [R4]. Another source makes the same separation, saying estimated weighting inherits an approximation term and is not exact [R3]. The method also requires the conditional law of Y given X to stay fixed [R8].

For label shift, the extension is described as reweighting conformal and calibration procedures when unlabeled target data are available [R153]. A later label-shift application reports that, under stronger shift, all methods lose some coverage because density ratios are estimated from pseudo-labels [R84].

Barber et al. use weighted quantiles to gain robustness to drift, and a new randomization technique for nonsymmetric algorithms [R12]. The abstract describes the new methods as provably robust, with substantially less loss of coverage when exchangeability is violated due to distribution drift or other challenging features of real data [R12].

Adaptive conformal inference proves long-run coverage frequency without assumptions on the data process [R8]. Approximate marginal coverage at most time steps is shown only when the shift is small and the predictor takes a simple form [R8]. Later work notes that ACI requires knowledge of the rate of change of the data-generating mechanism [R11].

Cauchois et al. develop methods for forming prediction sets that are valid whenever the two distributions are close in f-divergence [R8]. The robust validation method is reported to achieve nearly valid finite-sample coverage under only exchangeable training data [R139]. A fine-grained variant reweights the training samples to adjust for an identifiable covariate shift while protecting against worst-case conditional distribution shift bounded in an f-divergence ball [R23].

The supplied passages do not establish a single proof covering estimated weights together with mixed covariate and conditional shift for the original methods. One source lists simultaneous covariate and label shift with partially identifiable likelihood ratios as an open challenge [R4]. Another shows that, under unrestricted conditional shift, target coverage is only identified to the full interval from 0 to 1 [R3].

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 57 and set aside 63; 6 were read in full text and 51 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R2] Jef Jonkers, Glenn Van Wallendael, Luc Duchateau et al.. Conformal Predictive Systems Under Covariate Shift. 2024. arXiv:2404.15018. https://arxiv.org/abs/2404.15018
[R3] Maha Moussa. Auditing Conformal Prediction under Distribution Shift: A Detectability Boundary, Exact Label-Budget Design, and Repair. 2026. doi:10.21203/rs.3.rs-10396495/v1. https://doi.org/10.21203/rs.3.rs-10396495/v1
[R4] Debarun Banerjee. Conformal Prediction Sets for Tabular Regression Under Covariate Shift. 2026. doi:10.21203/rs.3.rs-9822449/v1. https://doi.org/10.21203/rs.3.rs-9822449/v1
[R8] Isaac Gibbs, Emmanuel J. Candès. Adaptive Conformal Inference Under Distribution Shift. 2021. arXiv:2106.00170. https://arxiv.org/abs/2106.00170
[R11] Isaac Gibbs, Emmanuel J. Candès. Conformal Inference for Online Prediction with Arbitrary Distribution Shifts. 2022. doi:10.48550/arxiv.2208.08401. https://doi.org/10.48550/arxiv.2208.08401
[R12] Rina Foygel Barber, Emmanuel J. Candès, Aaditya Ramdas et al.. Conformal prediction beyond exchangeability. 2023. doi:10.1214/23-aos2276. https://doi.org/10.1214/23-aos2276
[R23] Jiahao Ai, Zhimei Ren. Not all distributional shifts are equal: Fine-grained robust conformal inference. 2024. doi:10.48550/arxiv.2402.13042. https://doi.org/10.48550/arxiv.2402.13042
[R29] Ryan J. Tibshirani, Rina Foygel Barber, Emmanuel J. Candès et al.. Conformal Prediction Under Covariate Shift. 2019. doi:10.48550/arxiv.1904.06019. https://doi.org/10.48550/arxiv.1904.06019
[R84] Hyeonsu Lee, Ju‐Yeon Kim, Erkhembayar Jadamba et al.. Split Conformal Prediction with Label-Shift-Adjusted Bayesian Scores. 2026. doi:10.48550/arxiv.2609.12386. https://doi.org/10.48550/arxiv.2609.12386
[R139] Maxime Cauchois, Suyash Gupta, Alnur Ali et al.. Robust Validation: Confident Predictions Even When Distributions Shift. 2023. doi:10.1080/01621459.2023.2298037. https://doi.org/10.1080/01621459.2023.2298037
[R153] Aleksandr Podkopaev, Aaditya Ramdas. Distribution-free uncertainty quantification for classification under label shift. 2021. doi:10.48550/arxiv.2103.03323. https://doi.org/10.48550/arxiv.2103.03323
