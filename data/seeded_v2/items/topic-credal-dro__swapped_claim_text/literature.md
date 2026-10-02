## Literature review

The supplied passages say nothing direct about credal ambiguity sets such as the imprecise Dirichlet model or an epsilon-contamination neighborhood. They contain no head-to-head comparison of credal, Wasserstein and mean-covariance sets under a common cross-validation or calibration rule. What follows therefore covers only the Wasserstein and moment-based evidence, and then states what is missing.

For Wasserstein balls, the foundational source states that concentration results place the true distribution in the ball with confidence 1 - β when the radius is suitably chosen [R7]. It adds that the optimal value of the robust problem then gives an upper confidence bound on out-of-sample cost [R7]. A moment-uncertainty model was reported to give better-performing policies in a data-driven portfolio example [R7]. The same experiments found that the reliability of the guarantee was nondecreasing in the radius [R7]. A multistage control study reports the same pattern at N = 20, with an optimal radius that is neither too small nor too large [R37].

The same foundational study calibrated the radius by a bootstrap-style resampling procedure with held-out validation samples [R7]. In that study the Wasserstein solutions tended to beat SAA and LCX solutions in out-of-sample performance [R7]. The LCX set there was a moment-type comparator whose size was calibrated by bootstrapping to a target reliability, so this is not a mean-covariance set tuned under an identical rule [R7].

On moment-based sets, one survey-style comparison notes that they seem to be more tractable than Wasserstein sets [R7]. In its mean-risk portfolio experiments, out-of-sample performance improved up to a critical radius and then deteriorated [R66]. Another moment-based minimax study found its solutions close to data-driven ones under normal distributions and better under extremal distributions [R83].

On small samples, a multistage Wasserstein study reports that its models could outperform other multistage benchmarks when data are scarce [R52]. On contamination, one framework based on trimmings is said to address decision problems under contaminated samples, illustrated on newsvendor and portfolio problems [R57].

On calibration, one source finds that a theory-driven radius choice matches cross-validation for a Wasserstein regression estimator, but in a high-dimensional regression setting rather than a portfolio or newsvendor problem [R5].

What is not established is thus substantial. No passage evaluates credal sets, imprecise Dirichlet models or epsilon-contamination neighborhoods at all. No passage compares the three families across n of about 10 to 200 or contamination of 0 to 20% under a common tuning rule. No passage tests whether the cost guarantee stays reliable when a fraction of the sample is contaminated. The Wasserstein evidence on reliability concerns clean i.i.d. data, and the moment-based evidence is not matched to it in tuning or design.

## References

[R5] Liviu Aolaritei, Soroosh Shafiee, Florian Dörfler. Wasserstein Distributionally Robust Estimation in High Dimensions: Performance Analysis and Optimal Hyperparameter Tuning. 2022. arXiv:2206.13269. https://arxiv.org/abs/2206.13269
[R7] Peyman Mohajerin Esfahani, Daniel Kühn. Data-Driven Distributionally Robust Optimization Using the Wasserstein Metric: Performance Guarantees and Tractable Reformulations. 2015. arXiv:1505.05116. https://arxiv.org/abs/1505.05116
[R37] Insoon Yang. Wasserstein Distributionally Robust Stochastic Control: A Data-Driven Approach. 2020. doi:10.1109/tac.2020.3030884. https://doi.org/10.1109/tac.2020.3030884
[R52] Shixuan Zhang, Xu Andy Sun. On Distributionally Robust Multistage Convex Optimization: Data-driven Models and Performance. 2022. arXiv:2210.08433. https://arxiv.org/abs/2210.08433
[R57] Adrián Esteban-Pérez, Juan Miguel Morales. Distributionally robust stochastic programs with side information based on trimmings -- Extended version. 2020. doi:10.1007/s10107-021-01724-0. https://doi.org/10.1007/s10107-021-01724-0
[R66] Erick Delage, Yinyu Ye. Distributionally Robust Optimization Under Moment Uncertainty with Application to Data-Driven Problems. 2010. doi:10.1287/opre.1090.0741. https://doi.org/10.1287/opre.1090.0741
[R83] Dimitris Bertsimas, Xuan Vinh Doan, Karthik Natarajan et al.. Models for Minimax Stochastic Linear Optimization Problems with Risk Aversion. 2010. doi:10.1287/moor.1100.0445. https://doi.org/10.1287/moor.1100.0445
