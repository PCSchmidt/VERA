# Second problem: the baseline reproduction (2026-10-04)

The parent's experiment (Chen et al., arXiv 2601.21324, Section 5.2) run through the parent's own tool in `vera-sandbox-credal:506c17f` (the repository at commit 506c17fc, MOSEK replaced by Clarabel), 100 replications per method, against the target registered 2026-10-04T13:30:14Z (sha256 `142cf11e8512`) before any run. Units of 1e4.

| LV | this run mean (SD) | paper Table 3 mean (SD) | relative difference | within 5% |
|---|---|---|---|---|
| MAE (1e4) | 10.684 (0.7) | 10.7 (0.72) | -0.1% | yes |
| RMSE (1e4) | 12.182 (0.746) | 12.2 (0.77) | -0.1% | yes |
| p98 absolute error (1e4) | 21.852 (1.183) | 21.9 (1.23) | -0.2% | yes |
| CVaR 2% absolute error (1e4) | 23.881 (1.072) | 23.9 (1.1) | -0.1% | yes |

LV is best of the five methods on all four metrics: yes. The loop's baseline-gate rule says: accept.

| Method | MAE (paper) | RMSE (paper) | p98 (paper) | CVaR 2% (paper) | seconds per replication |
|---|---|---|---|---|---|
| cvar | 12.968 (13.0) | 14.371 (14.4) | 24.676 (24.7) | 27.237 (27.2) | 17.58 |
| wass | 12.774 (12.3) | 14.203 (13.7) | 24.903 (24.3) | 27.163 (26.5) | 41.75 |
| ridge | 13.211 (13.2) | 14.612 (14.6) | 25.186 (25.2) | 27.691 (27.7) | 0.0 |
| erm | 12.885 (12.7) | 14.31 (14.1) | 25.02 (24.7) | 28.043 (27.7) | 1.03 |

LV: 1.74 s per replication (the paper's Table 4: 1.44 for LV, 5.47 for CVaR, 6.16 for Wasserstein, on MOSEK and another machine; times are reported, never gated). Wasserstein's MAE differs from the paper's by about 4%: inside the registered 5% for LV, which is the row the gate reads, and reported for the others.

## What it took

- 2026-10-04T13:41:11Z: setup-lv failed. the package does not install its SLURM template, which `setup-lv` reads next to main.py: copied into the image.
- 2026-10-04T13:52:16Z: batch failed. numpy 2.4 raises on the parent's `np.sum(<generator>)`: numpy pinned below 2.3.
- 2026-10-04T14:02:27Z: batch failed. cvxpy 1.9 no longer has `cp.settings.PARAM_THRESHOLD`: cvxpy pinned below 1.8.
- 2026-10-04T14:12:03Z: batch failed. Geo-block CV 'no finite fold scores': the parent passes MOSEK-only options (`mosek_params`) that Clarabel rejects, and its cross-validation swallows the error: the options are dropped.
- 2026-10-04T14:22:44Z: batch failed. the same symptom from a second MOSEK-only option (`accept_unknown`): found by wrapping `Problem.solve` to print the swallowed error; dropped.
- 2026-10-04T14:47:10Z: batch failed after about 6 minutes. `cannot pickle 'DefaultSolver'`: a solved cvxpy problem holding a Clarabel solver is sent to joblib workers; the solver cache is cleared first.
- 2026-10-04T15:06:46Z: batch completed (5/5 configurations, 100 replications each, about 19 minutes on 8 CPUs). the parent's `csv` step then ran over an hour at 100% CPU on five 13 MB files and was stopped at 16:23Z; the harness joins the per-configuration files itself.
- 2026-10-04T16:24:11Z: result read from the finished batch (`--reuse`). the baseline run of record.

Each failure exposed a way the parent's repository does not run as published in a fresh environment: its dependencies are not pinned (`numpy>=1.26.2`, `cvxpy>=1.4.2`), it leans on a solver whose licence is personal, and it hides solver errors. The changes are in `docker/sandbox-credal/` (Dockerfile and `patch_solver.py`); the clone is not committed (the repository has no licence file).
