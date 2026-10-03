# Issue filed on ThalesGroup/treehfd: https://github.com/ThalesGroup/treehfd/issues/10

Status: **filed 2026-10-03** under Chris's account, on his go-ahead. Before filing, upstream `main` was rechecked: still commit `dd02152`, the unseeded `default_rng().choice` still at `src/treehfd/cartesian_partition.py` line 215, and the repo had no issues. The text below is as filed (path corrected from the first draft).
Evidence: `docs/results/treehfd_baseline_first_runs.md` (finding 2) and `docker/sandbox-treehfd/harness.py`.
Before filing, re-run the reproduction below against the current `main`; this was observed on commit `dd02152`
(version 1.4.2) only.

---

**Title:** `predict` is not deterministic: ties between nearest empty cells are broken with an unseeded RNG

**What happens.** For rows that fall in a cartesian cell with no training sample, `predict` merges the row with the
nearest cell and breaks distance ties with `np.random.default_rng()` created without a seed
(`src/treehfd/cartesian_partition.py`, line 215 in `predict_partition`). Two identical calls on the same fitted model can therefore
return different interaction predictions.

**Observed.** On the UCI Airfoil Self-Noise data (n = 1503, 5 features, an `XGBRegressor` with 100 trees, TreeHFD with
`interaction_order=2`, a 70/30 split), two consecutive `predict` calls on the same test rows gave interaction
predictions that differ by up to 0.97. Held-out residual MSE (relative to the ensemble's predictions) can therefore
change from call to call. (We did not measure how much of the variation across seeds comes from this tie-break.)

**Why it matters.** Results that depend on the held-out rows (any benchmark or paper table computed on test data) are not
reproducible from a seed, and a user cannot tell which part of the variation comes from the data split and which from
this tie-break.

**Reproduction (sketch).**

```python
model = XGBRegressor(n_estimators=100).fit(X_train, y_train)
hfd = XGBTreeHFD(model); hfd.fit(X_train, interaction_order=2)
a = hfd.predict(X_test); b = hfd.predict(X_test)
print(max(abs(a_i - b_i).max() for a_i, b_i in zip(a, b)))  # non-zero on Airfoil
```

**Suggested fix.** Take a `random_state` in `fit` or `predict` (or in the constructor) and pass it to
`default_rng`; or break ties deterministically (for example, the lowest cell index).

**Workaround we use.** We make every no-argument `default_rng()` deterministic inside our harness; the tie choice stays
arbitrary but fixed.

Thank you for the package; we use it as the baseline of a research-agent benchmark and found this while reproducing
Table 2 of the NeurIPS 2025 paper.
