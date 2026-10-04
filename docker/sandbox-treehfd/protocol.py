"""The registered protocol experiment for the tree-explain question (Increment 4). Runs INSIDE the sandbox.

For each pairwise correlation rho of the analytical case and each method (TreeHFD, TreeSHAP, and any idea's method):

- `component_mse`: sum over every component J of mean((eta_hat_J - eta_J)^2) on held-out rows, plus (eta0_hat - eta0)^2,
  against the closed-form true HFD of `truth.py` (checked against the paper's Table 3); a component the method does
  not return counts as zero. `component_mse_pct` is that sum as a percentage of the variance of the true signal.
- `residual_mse_pct`: as in harness.py (the method's components against the fitted ensemble).
- `rank_stability`: B bootstrap refits of the ensemble (rows resampled), the method run on each, the importance of a
  component taken as its variance over fixed held-out rows; the mean Spearman correlation of the importance vector
  over all pairs of refits (1 = the same ranking every time). `rank_vs_truth`: the Spearman correlation of the
  method's importances (main fit) with the true components' importances.
- `runtime_s`, and `own_variables_only`: whether every component is a function of its own variables alone (the check
  of harness.py, run once per method and rho on the first seed). TreeHFD must pass it. TreeSHAP's path-dependent values
  are not functions of the variables of their component, so for the reference method TreeSHAP the result is
  reported, not enforced.

All values are measured here; none is a reported figure of the paper.
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path

import harness
import numpy as np
import truth
import xgboost as xgb
from numpy.random import default_rng
from scipy.stats import spearmanr

TEST_ROWS_FOR_IMPORTANCE = 1000
KEYS = [(j,) for j in range(truth.DIM)] + list(truth.PAIRS)


def treeshap(model, X_train, X_test):
    """xgboost's TreeSHAP (path-dependent) with interactions: main effect j is the diagonal, the pair (a, b) the sum of
    the two off-diagonal entries; the bias is the constant term."""
    m = model.get_booster().predict(xgb.DMatrix(X_test), pred_interactions=True)
    comps = {(j,): m[:, j, j] for j in range(truth.DIM)}
    for a, b in truth.PAIRS:
        comps[(a, b)] = m[:, a, b] + m[:, b, a]
    return float(m[0, -1, -1]), comps


REFERENCE_METHODS = {"treehfd": harness.baseline, "treeshap": treeshap}
ENFORCE_OWN_VARIABLES = {"treehfd": True, "treeshap": False}  # a method from an idea is always enforced


def importance(comps: dict, X_rows: int) -> np.ndarray:
    return np.array([float(np.var(np.asarray(comps[k])[:X_rows])) if k in comps else 0.0 for k in KEYS])


def rank_corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None  # a constant vector has no ranking
    return float(spearmanr(a, b).statistic)


def cell(method, name: str, rho: float | None, seeds: int, n_boot: int, data_dir: Path) -> dict:
    """One (method, dataset) cell, the metrics over `seeds` data draws, with their values. `rho` None is the registered
    public dataset (Airfoil): it has no true components, so only the residual, the stability and the runtime."""
    keep = {"component_mse": [], "component_mse_pct": [], "residual_mse_pct": [], "rank_stability": [],
            "rank_vs_truth": [], "runtime_s": []}  # fmt: skip
    own_vars: bool | str | None = None
    enforce = ENFORCE_OWN_VARIABLES.get(name, True)
    for seed in range(seeds):
        X, y, X_test = harness.analytical(seed, data_dir, rho) if rho is not None else harness.airfoil(seed, data_dir)
        model = xgb.XGBRegressor(n_estimators=harness.N_ESTIMATORS, n_jobs=2, random_state=seed).fit(X, y)
        t0 = time.perf_counter()
        eta0, comps = method(model, X, X_test)
        runtime = time.perf_counter() - t0
        problem = harness.validate_shape(eta0, comps, len(X_test), X.shape[1])
        if problem:
            return {"valid": False, "invalid_reason": problem}
        if seed == 0:  # does every component depend only on its own variables? (run once per cell)
            _, _, _, bad = harness.run_method(method, model, X[:2000], X_test[:500], seed)
            own_vars = bad is None
            if bad and enforce:
                return {"valid": False, "invalid_reason": bad}
        if rho is not None:
            t_eta0, truth_comps = truth.true_components(rho, X_test)
            err = (eta0 - t_eta0) ** 2 + sum(
                float(np.mean((np.asarray(comps.get(k, np.zeros(len(X_test)))) - truth_comps[k]) ** 2)) for k in KEYS
            )
            signal = t_eta0 + sum(truth_comps.values())
        pred = model.predict(X_test)
        hfd = eta0 + sum(np.asarray(v) for v in comps.values())
        imp = importance(comps, TEST_ROWS_FOR_IMPORTANCE)
        if rho is not None:
            keep["component_mse"].append(float(err))
            keep["component_mse_pct"].append(float(100 * err / np.var(signal)))
        keep["residual_mse_pct"].append(harness.residual_pct(pred, hfd))
        keep["runtime_s"].append(runtime)
        if rho is not None:
            truth_imp = np.array([float(np.var(truth_comps[k][:TEST_ROWS_FOR_IMPORTANCE])) for k in KEYS])
            rv = rank_corr(imp, truth_imp)
            if rv is not None:
                keep["rank_vs_truth"].append(rv)
        boot_imps = []
        rng = default_rng(seed + 5000)
        for b in range(n_boot):
            idx = rng.integers(0, len(X), len(X))
            mb = xgb.XGBRegressor(n_estimators=harness.N_ESTIMATORS, n_jobs=2, random_state=seed * 100 + b)
            mb.fit(X[idx], y[idx])
            _, cb = method(mb, X[idx], X_test[:TEST_ROWS_FOR_IMPORTANCE])
            boot_imps.append(importance(cb, TEST_ROWS_FOR_IMPORTANCE))
        pairs = [rank_corr(a, b) for a, b in itertools.combinations(boot_imps, 2)]
        pairs = [p for p in pairs if p is not None]
        if pairs:
            keep["rank_stability"].append(float(np.mean(pairs)))
    out: dict = {"valid": True, "invalid_reason": None, "n_seeds": seeds, "n_boot": n_boot,
                 "own_variables_only": own_vars}  # fmt: skip
    for k, vals in keep.items():
        out[k] = harness.summary(vals) if vals else None
    return out


def run_protocol(methods: dict, datasets: list[str], seeds: int, n_boot: int, data_dir: Path) -> dict:
    """{method name: {dataset: cell}}, a dataset being `analytical@<rho>` or `airfoil`; a method that raises is
    recorded with its error, not raised."""
    results: dict = {}
    for name, method in methods.items():
        results[name] = {}
        for ds in datasets:
            rho = None if ds == "airfoil" else float(ds.split("@")[1])
            try:
                results[name][ds] = cell(method, name, rho, seeds, n_boot, data_dir)
            except Exception as exc:  # noqa: BLE001 - recorded in the table for the reader
                results[name][ds] = {"valid": False, "invalid_reason": f"raised {type(exc).__name__}: {exc}"[:300]}
    return results
