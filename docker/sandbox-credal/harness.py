# ruff: noqa: E501
"""Trusted experiment harness for the credal-ambiguity-sets loop (Increment 4). Runs INSIDE the sandbox; written by VERA.

The parent problem (docs/results/credal_baseline_target.json): linear regression with the absolute loss on California
Housing under an East-to-West geographic shift, the parent's method LV against CVaR, Wasserstein, ridge and ERM.

- `--method baseline` runs the parent's own experiment through its command-line tool (`credaldro setup-lv
  lv_california_housing_val`, `batch`, `csv`), reads its per-replication results, and reports each of the five methods'
  mean and spread on the four registered metrics (units of 1e4). The harness's own baseline row, the one ideas are
  compared with, is LV.
- `--method /work/method.py` runs an idea: `fit_predict(X_train, y_train, X_test) -> y_pred` (a model for the housing
  value), on the parent's geographic split (`credal_dro.dataset.california_housing_split_geographic`, axis 0, gap
  ratio 0.30, one split per replication seed), with the parent's metric code. The harness computes the metrics; the
  idea never sees the test labels. Validity: predictions finite, the right length, and unchanged when the training
  rows are given in another order (an idea may not depend on row order).

Usage (in the container): python harness.py --method baseline|/work/method.py --out /work/result.json
         [--seeds N] [--data-dir /work/data]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

UNIT = 1e4
GAP_RATIO = 0.30
ALGORITHMS = {"lv_bas_ch": "lv", "cvar_lad": "cvar", "wass_lad": "wass", "erm_ridge": "ridge", "erm_lad": "erm"}
METRICS = ("mae", "rmse", "p98_abs_error", "cvar_abs_error")
EXPERIMENT = "lv_california_housing_val"


def summary(values: list[float]) -> dict:
    return {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "values": [float(v) for v in values]}  # fmt: skip


# ── the parent's own experiment ─────────────────────────────────────────────────────────────────────


def run_parent(data_dir: Path, work: Path, n_expected: int) -> dict:
    """Run the parent's experiment through its CLI; return {method: {metric: summary, 'total_time_s': summary}}."""
    exp, runs = work / "exp", work / "expdata"
    env = {**os.environ, "CALIFORNIA_HOUSING_DATASET_DIR": str(data_dir), "OMP_NUM_THREADS": "1"}
    for args in (
        ["setup-lv", EXPERIMENT, str(exp), "--overwrite", "--experiment-data-dir", str(runs)],
        ["batch", str(exp), "0", "99999", "--experiment-data-dir", str(runs)],
        ["csv", str(exp), "--experiment-data-dir", str(runs)],
    ):
        proc = subprocess.run(["credaldro", *args], env=env, capture_output=True, text=True)
        (work / f"log_{args[0]}.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            text = [ln for ln in (proc.stderr + proc.stdout).splitlines() if ln.strip() and ln[0] not in "│╭╰"]
            raise RuntimeError(f"credaldro {args[0]} failed: " + " | ".join(text[-6:])[-900:])
    df = pd.read_csv(runs / "results.csv")
    out: dict = {}
    for algo, name in ALGORITHMS.items():
        rows = df[df["algorithm"] == algo]
        if rows.empty:
            out[name] = {"valid": False, "invalid_reason": f"no rows for algorithm {algo} in the parent's results"}
            continue
        finite = all(np.isfinite(pd.to_numeric(rows[m], errors="coerce")).all() for m in METRICS)
        cell: dict = {"valid": bool(finite) and len(rows) == n_expected, "n": int(len(rows))}
        if not finite:
            cell["invalid_reason"] = "a metric is not finite"
        elif len(rows) != n_expected:
            cell["invalid_reason"] = f"{len(rows)} replications, the registered number is {n_expected}"
        for m in METRICS:
            cell[m] = summary([float(v) / UNIT for v in rows[m]])
        total = sum(pd.to_numeric(rows[c], errors="coerce").fillna(0.0) for c in ("validation_time", "solve_time", "likelihood_time") if c in rows)
        cell["runtime_s"] = summary([float(v) for v in total])
        out[name] = cell
    return out


# ── an idea's method ────────────────────────────────────────────────────────────────────────────────


def load_method(spec: str):
    module_spec = importlib.util.spec_from_file_location("loop_method", spec)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.fit_predict


def parent_splits(seed: int, data_dir: Path) -> dict:
    os.environ["CALIFORNIA_HOUSING_DATASET_DIR"] = str(data_dir)
    from credal_dro.dataset import california_housing_split_geographic

    return california_housing_split_geographic(axis=0, seed=seed, standardise_y=False, gap_ratio=GAP_RATIO)


def metrics_of(abs_errors: np.ndarray) -> dict:
    from credal_dro.dataset import empirical_cvar

    return {"mae": float(np.mean(abs_errors)) / UNIT, "rmse": float(np.sqrt(np.mean(abs_errors**2))) / UNIT,
            "p98_abs_error": float(np.quantile(abs_errors, 0.98)) / UNIT,
            "cvar_abs_error": float(empirical_cvar(abs_errors, tail_mass=0.02)) / UNIT}  # fmt: skip


def evaluate_idea(method, seeds: int, data_dir: Path) -> dict:
    per_metric: dict[str, list[float]] = {m: [] for m in METRICS}
    runtimes = []
    for seed in range(seeds):
        sp = parent_splits(seed, data_dir)
        X = np.concatenate([sp["X_train"], sp["X_select"]], axis=0)
        y = np.concatenate([sp["y_train"], sp["y_select"]], axis=0)
        X_test, y_test = sp["X_test"], sp["y_test"]
        t0 = time.perf_counter()
        pred = np.asarray(method(X.copy(), y.copy(), X_test.copy()), dtype=float).reshape(-1)
        runtimes.append(time.perf_counter() - t0)
        if pred.shape != (len(y_test),) or not np.all(np.isfinite(pred)):
            return {"valid": False, "invalid_reason": "predictions must be a finite array with one value per test row"}
        order = np.random.default_rng(seed + 1000).permutation(len(y))
        again = np.asarray(method(X[order].copy(), y[order].copy(), X_test.copy()), dtype=float).reshape(-1)
        if not np.allclose(pred, again, rtol=1e-4, atol=1e-6 * max(float(np.abs(pred).max()), 1.0)):
            return {"valid": False, "invalid_reason": "predictions change when the training rows are reordered"}
        for m, v in metrics_of(np.abs(y_test - pred)).items():
            per_metric[m].append(v)
    return {"valid": True, "invalid_reason": None, "n_seeds": seeds, **{m: summary(v) for m, v in per_metric.items()},
            "runtime_s": summary(runtimes)}  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="baseline")
    ap.add_argument("--out", default="/work/result.json")
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--data-dir", default="/work/data")
    ap.add_argument("--datasets", default="california_housing", help="accepted for the loop's driver; one dataset exists")
    args = ap.parse_args(argv)
    out: dict = {"method": args.method, "datasets": {}}
    data_dir = Path(args.data_dir)
    try:
        if args.method == "baseline":
            methods = run_parent(data_dir, Path(args.out).parent, args.seeds)
            lv = methods["lv"]
            out["datasets"]["california_housing"] = {
                **lv, "n_seeds": args.seeds, "reference_methods": {k: v for k, v in methods.items() if k != "lv"}}
        else:
            out["datasets"]["california_housing"] = evaluate_idea(load_method(args.method), args.seeds, data_dir)
    except Exception:  # the method's own error: reported, not raised
        out["error"] = traceback.format_exc()[-1500:]
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out)[:2000])


if __name__ == "__main__":
    main()
