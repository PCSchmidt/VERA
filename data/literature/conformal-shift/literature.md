## Literature review

The weighted conformal prediction of Tibshirani et al. is described in the supplied abstract as producing distribution-free prediction intervals when test and training covariate distributions differ [R29]. A secondary source states the marginal guarantee as holding provided the likelihood ratios are exactly known [R4]. Gibbs and Candès's related-work summary says that the Tibshirani et al. reweighting approach requires the conditional distribution of Y given X to be constant between training and testing, and the likelihood ratio to be known or very accurately estimated [R8].

For estimated weights, the supplied sources give only partial coverage. One audit paper says that estimated weighted conformal prediction inherits an approximation term and is not relabeled exact [R3]. Another source reports that coverage degrades at a rate controlled by the estimation error [R4]. A training-conditional analysis says its results extend to estimated likelihood ratios [R67]. Another paper reports that weighted conformal prediction can undercover substantially when the density ratio is unbounded or must be learned [R32].

Barber et al. use weighted quantiles to gain robustness to drift, together with a randomization technique for nonsymmetric algorithms [R12]. The supplied abstract states that the methods lose substantially less coverage under violated exchangeability, but it gives no explicit coverage bound.

Adaptive conformal inference makes no assumption on the data process: its abstract says it provably achieves the desired coverage frequency over long-time intervals irrespective of the true data generating process [R8]. For adaptive conformal inference, the authors state that when the distribution shift is small and the prediction algorithm takes a certain simple form, it will additionally obtain approximate marginal coverage at most time steps [R8]. A later paper notes that ACI requires knowledge of the rate of change of the data-generating mechanism [R11].

For f-divergence methods, Cauchois et al. are summarized as valid whenever the two distributions are close in f-divergence [R8]. The robust validation paper's abstract says its conformal-based method achieves nearly valid coverage in finite samples, under only the condition that the training data be exchangeable [R139].

One label-shift paper reports that under stronger shift, all methods incur some coverage loss due to pseudo-label-based density-ratio estimation [R84]. Mixed covariate and conditional shift is also flagged as open, since one source calls simultaneous covariate and label shift with partially identifiable likelihood ratios an open challenge [R4]. Under unrestricted conditional shift, one audit paper shows that target coverage is only identified to the full interval from 0 to 1 [R3].

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 160 candidate papers. A relevance screen kept 57 and set aside 103; 6 were read in full text and 51 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R3] Maha Moussa. Auditing Conformal Prediction under Distribution Shift: A Detectability Boundary, Exact Label-Budget Design, and Repair. 2026. doi:10.21203/rs.3.rs-10396495/v1. https://doi.org/10.21203/rs.3.rs-10396495/v1
[R4] Debarun Banerjee. Conformal Prediction Sets for Tabular Regression Under Covariate Shift. 2026. doi:10.21203/rs.3.rs-9822449/v1. https://doi.org/10.21203/rs.3.rs-9822449/v1
[R8] Isaac Gibbs, Emmanuel J. Candès. Adaptive Conformal Inference Under Distribution Shift. 2021. arXiv:2106.00170. https://arxiv.org/abs/2106.00170
[R11] Isaac Gibbs, Emmanuel J. Candès. Conformal Inference for Online Prediction with Arbitrary Distribution Shifts. 2022. doi:10.48550/arxiv.2208.08401. https://doi.org/10.48550/arxiv.2208.08401
[R12] Rina Foygel Barber, Emmanuel J. Candès, Aaditya Ramdas et al.. Conformal prediction beyond exchangeability. 2023. doi:10.1214/23-aos2276. https://doi.org/10.1214/23-aos2276
[R29] Ryan J. Tibshirani, Rina Foygel Barber, Emmanuel J. Candès et al.. Conformal Prediction Under Covariate Shift. 2019. doi:10.48550/arxiv.1904.06019. https://doi.org/10.48550/arxiv.1904.06019
[R32] James Wang, Surbhi Goel. Weight Clipping for Robust Conformal Inference under Unbounded Covariate Shifts. 2026. doi:10.48550/arxiv.2605.02072. https://doi.org/10.48550/arxiv.2605.02072
[R67] Mehrdad Pournaderi. Sharp training-conditional coverage for conformal prediction under covariate shift. 2026. doi:10.48550/arxiv.2609.33456. https://doi.org/10.48550/arxiv.2609.33456
[R84] Hyeonsu Lee, Ju‐Yeon Kim, Erkhembayar Jadamba et al.. Split Conformal Prediction with Label-Shift-Adjusted Bayesian Scores. 2026. doi:10.48550/arxiv.2609.12386. https://doi.org/10.48550/arxiv.2609.12386
[R139] Maxime Cauchois, Suyash Gupta, Alnur Ali et al.. Robust Validation: Confident Predictions Even When Distributions Shift. 2023. doi:10.1080/01621459.2023.2298037. https://doi.org/10.1080/01621459.2023.2298037
