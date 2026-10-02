## Abstract

We ran a small automated research loop to try to improve TreeHFD [R1], a method that decomposes an xgboost model [R2] into main effects and second-order interactions. The loop generated 3 ideas and ran 2 of them on a subset of the problem. Neither beat the baseline on every dataset. This is a negative result. One idea (C3) lowered held-out residual MSE on Analytical at more than double the runtime, and did nothing on Airfoil. The other (C1) was worse on Analytical and unchanged on Airfoil.

## Method

**Setup.** Datasets: Analytical and Airfoil. We used 3 seeds, xgboost with 100 trees, and held-out data. The metric is Residual MSE (%), where lower is better. Runtime in seconds is also reported. The baseline reproduction passed its gate: it matched the paper's reference values within the registered tolerance. The paper's convention is in-sample residual MSE, where the baseline gives 0.570 on Analytical and 1.52 on Airfoil. The results table reports held-out values, which are higher, so the table numbers should not be compared directly with those in-sample figures.

**Ideas run.**

- **C3, residual-pair greedy refinement.** Fit TreeHFD with main effects only, or with a small interaction list. Compute the model's residual on the training data. Score each candidate pair by how much residual variance a 2D binned-mean smoother on that pair explains. Add the top pairs to interaction_list and refit, repeating once or twice. The aim is to target the interactions that reduce the residual most.
- **C1, importance-ranked interaction selection.** Compute pair importance from the xgboost trees by summing gain over splits where a variable is split below an ancestor on another variable, per unordered pair. Pass the top-K pairs (K around 2p) as interaction_list to XGBTreeHFD. The aim is to fit fewer components, cutting runtime, while keeping the pairs that carry real interactions.

A third idea was generated but not run.

## Results

Results from a research-loop run on the TreeHFD problem (mean ± std over 3 seeds). ↓ = lower is better; ↑ = higher is better.

| Method | Analytical · Residual MSE (%) ↓ | Analytical · Runtime (s) ↓ | Airfoil · Residual MSE (%) ↓ | Airfoil · Runtime (s) ↓ |
|---|---|---|---|---|
| TreeHFD (baseline) | 2.79 ± 0.32 | 27.5 ± 0.58 | 4.73 ± 0.11 | 3.42 ± 0.058 |
| C3: Residual-pair greedy refinement | 2.47 ± 0.20 | 60.8 ± 2.4 | 4.73 ± 0.11 | 11.3 ± 0.41 |
| C1: Importance-ranked interaction selection | 2.97 ± 0.27 | 23.9 ± 0.86 | 4.73 ± 0.11 | 3.43 ± 0.088 |

Values are mean ± std over 3 seeds.

- **C3** reduced Analytical residual MSE from 2.79 ± 0.32 to 2.47 ± 0.20. The gap is about one baseline standard deviation, so with 3 seeds we cannot call it reliable. Runtime rose from 27.5 s to 60.8 s on Analytical and from 3.42 s to 11.3 s on Airfoil. On Airfoil its MSE was identical to the baseline (4.73 ± 0.11).
- **C1** raised Analytical residual MSE to 2.97 ± 0.27, slightly worse than baseline and within noise. Runtime fell from 27.5 s to 23.9 s on Analytical. On Airfoil, MSE (4.73 ± 0.11) and runtime (3.43 s versus 3.42 s) matched the baseline.

The identical Airfoil MSE for both ideas and the baseline suggests that, on that dataset, the changes may not have altered the fitted decomposition. We did not investigate why.

**Outcome:** no idea beat the baseline on every dataset.

## Limitations

- Only 3 seeds, so the differences on Analytical are within or near the noise.
- Only two datasets and one model configuration (xgboost with 100 trees).
- Only 2 of 3 ideas were run, and on a subset of the problem.
- The ideas were produced and implemented by a language model, and the implementations were not independently reviewed. The Airfoil results identical to the baseline could reflect an implementation issue.
- Held-out numbers differ from the paper's in-sample convention, so they are not directly comparable to the reference values.
- The loop was crude. It established that these two simple variants give no clear gain, and that C3 costs substantially more time. It did not establish that the underlying ideas cannot work.

## References

[R1] Clément Bénard. Tree Ensemble Explainability through the Hoeffding Functional Decomposition and TreeHFD Algorithm. 2025. arXiv:2510.24815. https://arxiv.org/abs/2510.24815
[R2] Tianqi Chen, Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. 2016. arXiv:1603.02754. https://arxiv.org/abs/1603.02754
