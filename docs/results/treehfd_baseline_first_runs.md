# TreeHFD baseline: first runs (2026-10-01, Increment 2)

The registered target is in [treehfd_baseline_target.json](treehfd_baseline_target.json), written before any run.
These are the first runs of the baseline through VERA's harness (`docker/sandbox-treehfd/harness.py`, in the
sandbox), 100 xgboost trees, 3 seeds, held-out data.

| Dataset | Measured Residual MSE (%) | Paper | Within the registered tolerance (±1.0 point)? |
|---|---|---|---|
| Analytical (n = 5000, p = 6) | 2.79 ± 0.32 | 2.0 (S-Mat) | yes |
| Airfoil (n = 1503, p = 5) | 4.73 ± 0.11 | 2.0 (Table 2) | **no** |

## Findings

1. **Airfoil is not reproduced under the registered protocol.** Nothing in the target was changed after seeing this.
   Diagnostic only (not a protocol change): measured **in-sample** (on the data the model and TreeHFD were fitted
   on), the Airfoil residual is 1.36-1.72% over three seeds, within the tolerance of the paper's 2%. The paper
   defines the residual as the MSE of TreeHFD against the ensemble, normalised by the ensemble's variance (S-Mat
   B.3.1) but does not say whether Table 2 is measured on training or held-out data. In-sample is the likelier
   reading. **Decision needed from Chris** before any run that includes Airfoil: keep held-out (stricter; Airfoil then
   fails as registered), or amend the target to in-sample for real datasets with a dated entry in its `changes`.
2. **treehfd's `predict` is not deterministic.** For rows that fall in a cartesian cell empty in training, it merges
   with the nearest cell and breaks ties with an unseeded `np.random.default_rng()`
   (`treehfd/cartesian_partition.py`, `predict_partition`). Identical calls gave interaction predictions differing
   by up to 0.97 on Airfoil. The harness makes every no-argument `default_rng()` deterministic, so runs are
   reproducible; the tie choice stays arbitrary. Worth reporting upstream (ThalesGroup/treehfd).
3. **Runtime** of the baseline: about 25 s per seed on the analytical case in the container (the paper says under a
   minute), about 3 s on Airfoil.

## First live run of the loop (smoke-004, analytical only, 3 seeds, GLM-5.3 Flash, $0.006)

All stages ran; every judge verdict matched its programmatic shadow answer. Two ideas were implemented and run;
neither beat the baseline (C1 depth-sweep ensemble 3.23%, C3 least-squares recalibration 2.95%, baseline 2.79%), and
the write-up reported that as a negative result. See `data/ledger/run_smoke-004.jsonl`.

## Both residuals (after the 2026-10-01 target change), 3 seeds, 100 trees

| Dataset | Held-out | In-sample | Paper | Matches the paper on |
|---|---|---|---|---|
| Analytical | 2.79 ± 0.32 | 0.57 ± 0.02 | 2.0 | held-out only |
| Airfoil | 4.73 ± 0.11 | 1.52 ± 0.15 | 2.0 | in-sample only |

No single row set reproduces the paper on both datasets. The paper says its analytical experiment uses an
independent testing dataset (Section 4, for Table 1) and does not say which row set Table 2 (the real datasets) uses.
Read that way, the paper's own text supports held-out for the analytical case and in-sample for the real datasets.
The target registered on 2026-10-01 applies in-sample uniformly, under which the analytical dataset fails
(0.57 against 2.0, tolerance 1.0). Open: whether to register the row set per dataset (see the target file's
`changes`); a second change made after seeing results, to be recorded as such.

## Per-dataset row sets registered; first full-protocol loop run (smoke-006, both datasets, 3 seeds, $0.0034)

The target now registers the reproduction row set per dataset (analytical held-out, Airfoil in-sample; second
change after seeing results, recorded in the target's `changes`). The baseline gate accepted the baseline on both
datasets, judge and programmatic check agreeing. Idea results (held-out / in-sample residual, %):

| Method | Analytical | Airfoil |
|---|---|---|
| TreeHFD (baseline) | 2.79 / 0.57 | 4.73 / 1.52 |
| C2 depth-variable tuning | 2.41 / 0.84 | 5.15 / 2.24 |
| C3 refit intercept residual | 31.35 / 25.76 | 36581 / 32441 |

C2 lowers the analytical held-out residual and raises Airfoil's, so it does not beat the baseline on every dataset;
no idea did, and the write-up said so. Findings on the way: GLM's hidden reasoning is unbounded at its default
(4 of 11 loop-judge calls used 5000-6000 tokens, one returned nothing), so the loop judge now sends
`reasoning: {effort: minimal}` (largest judge reply since: 1040 tokens); the T1 benchmark ran at the provider default,
so the Increment 2 re-test measures the path as configured here. A tie for "best method" is no longer put to the
judge. Ledger: `data/ledger/run_smoke-006.jsonl`.
