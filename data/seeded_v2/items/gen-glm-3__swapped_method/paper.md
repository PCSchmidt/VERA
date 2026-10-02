 # Improving TreeHFD: A Small Negative Result

## Abstract

TreeHFD decomposes a tree ensemble such as an xgboost model into main effects and pairwise interactions using the Hoeffding functional decomposition [R1]. We ran a crude automated improvement loop around the published method. We first reproduced the baseline within its registered tolerance, generated three improvement ideas, implemented two, and evaluated them on two datasets across three seeds. Neither implemented idea reduced residual mean squared error below the baseline on both datasets. One idea performed comparably at substantially increased runtime; the other sharply degraded accuracy despite running faster. This is a negative result reported as such: we make no claim that the tested modifications exhaust the space of possible improvements, nor that the untested third idea would have failed.

## Method

The task was to reduce residual MSE (%) — the gap between the full model prediction and the sum of its computed main-effect and interaction components — following the paper's conventions [R1].

**Baseline reproduction.** Before testing modifications, we reran the original TreeHFD pipeline under our setup: xgboost [R2] with 100 trees, three random seeds, evaluation on held-out data, on two datasets (Analytical, Airfoil). The reproduced values matched the paper's reference values within the pre-registered tolerance, so subsequent comparisons were made against a trusted implementation of the same procedure.

**Idea generation and selection.** Three candidate ideas were generated. Two were selected and fully implemented:

- **C3: Two-stage additive refit.** Run TreeHFD once to obtain initial components. Compute residuals r = f(x) minus the summed predicted components. For each component j, fit a small ridge regression g_j restricted to that component's own variables z_j, predicting r. Add correction functions h_j(z_j) on top of the original components. This preserves the structural property that each term depends only on its assigned variable set, while allowing a linear post-hoc adjustment to absorb systematic residual mass.

- **C1: Filter low-gain interactions.** Call TreeHFD with `interaction_order=1` together with a broad candidate list of interaction pairs via `interaction_list`. Inspect XGBoost's feature-pair split gains (equivalently, per-candidate residual reduction) to score pair importance. Refit TreeHFD retaining only the top-k highest-scoring interactions and discarding those judged negligible, aiming to remove noise terms whose inclusion inflates the residual without explanatory benefit.

One further generated idea was not run and remains unevaluated here.

**Evaluation protocol.** Both methods were compared head-to-head with the unchanged baseline on the identical splits, seeds, and metric. Lower residual MSE indicates a tighter decomposition. Runtimes were also recorded but treated as secondary.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C3: Two-stage additive refit | 2.80 ± 0.32 | 40.7 ± 2.5 | 4.74 ± 0.12 | 4.65 ± 0.034 |
| C1: Filter low-gain interactions | 26.6 ± 1.3 | 5.36 ± 0.039 | 40.8 ± 2.8 | 1.34 ± 0.050 |

No idea improved upon the baseline on both datasets, which was the success criterion adopted before the runs.

**C1 (two-stage additive refit)** essentially tied the baseline: 2.80 vs. 2.79 on Analytical and 4.74 vs. 4.73 on Airfoil — differences well inside seed variability. It cost roughly 48% more time on Analytical (40.7 s vs. 27.5 s) and about 36% more on Airfoil (4.65 s vs. 3.42 s). Under this test, the extra machinery bought nothing measurable.

**C1 (filter low-gain interactions)** achieved large speedups (about five times faster on Analytical, ~2.5× on Airfoil) but catastrophically worse fidelity: residual MSE rose to 26.6 on Analytical and 40.8 on Airfoil, versus baselines near 2.8–4.7. Filtering interactions down to the top-ranked pairs evidently removed far too much signal, suggesting either that the ranking heuristic misjudged which pairs matter for the *decomposition* objective (as opposed to raw predictive gain), or that k was set far too aggressively. Either way, the approach as implemented does not work.

We note that these held-out numbers exceed the in-sample figures cited during registration (e.g., 0.57 / 1.52 %), consistent with the general expectation that residual errors grow out-of-distribution; the comparison among methods used like-for-like held-out values throughout.

In summary: zero successful interventions out of two implemented attempts.

## Limitations

Several constraints bound how much can be concluded from this exercise.

- **Few seeds and few datasets.** Only two datasets and three seeds were used. Marginal claims (such as "within one standard deviation") rest on very thin evidence; a genuinely neutral effect cannot be separated from a tiny real effect at this sample size.
- **Single model configuration.** All experiments used one fixed xgboost setting (100 trees). Interactions behave differently with different depths, learning rates, or ensembles of other types, none of which were probed.
- **Crude ideation.** Ideas were proposed and implemented by a language model operating largely autonomously ("crude loop"). There was no human expert review step prior to execution, so some obvious design flaws — notably the aggressiveness of the filtering cutoff in C1 — went unchecked until after the expensive experiment had already been wasted.
- **Only a fraction of the idea pool explored.** Of three ideas generated, just two were executed. The remaining proposal might succeed where these two did not; nothing here rules it out.
- **Runtime reporting conditions differ across environments/hardware setups**, making absolute timing less reliable than relative rankings taken within the same run batch.
- **Metric scope limited.** Residual MSE captures closeness of the reconstruction to the underlying model function, but says little directly about downstream interpretive quality (e.g., whether plots of individual components look plausible). A method could conceivably trade slight residual increase for cleaner-looking explanations, and this dimension was invisible to us.

Given all of the above, the appropriate reading is narrow: two specific mechanisms — a per-component ridge-based refitting stage, and aggressive pruning of interaction candidates based on gradient-splitting statistics — did not help improve TreeHFD's residual performance under the particular settings tried. Broader conclusions about improving TreeHFD require larger-scale study.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
