"""Trusted experiment harness for the TreeHFD loop. Runs INSIDE the sandbox; written by VERA, not by the loop.

It fits the xgboost model, calls a decomposition method, and computes the metric itself, so agent-written code
never touches the numbers that get reported:

  residual = 100 * mean((ensemble_pred - hfd_pred)^2) / var(ensemble_pred)
  (TreeHFD paper, S-Mat B.3.1; hfd_pred = eta0 + sum of the method's components), reported on two row sets:
  residual_mse_pct        on held-out data: what ideas are compared on
  residual_in_sample_pct  on the data the model and the decomposition were fitted on: what the paper's Table 2
                          appears to report, so the baseline-reproduction gate uses it

A method is `decompose(model, X_train, X_test) -> (eta0, components)` where `components` maps a tuple of variable
indices, e.g. (3,) or (1, 4), to an array of length len(X_test). `--method baseline` is the parent's TreeHFD
(interaction order 2). Validity: every component must depend only on its own variables. One extra block of rows,
in which the other variables are taken from different rows, is appended to X_test; a component whose value changes
there is not a function of its variables alone, and the run is marked invalid (it cannot win by returning the
ensemble's own prediction as a "component").

Usage (in the container): python harness.py --method baseline|/work/method.py --out /work/result.json
         [--datasets analytical,airfoil] [--seeds 3] [--data-dir /work/data]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
import traceback
from pathlib import Path

import numpy as np
import xgboost as xgb
from numpy.random import default_rng
from treehfd import XGBTreeHFD

# treehfd breaks ties between equally near empty cells with an unseeded `np.random.default_rng()` in
# `predict` (cartesian_partition.py), so its predictions on rows in cells unseen in training change from call to
# call (found in Increment 2: component (0, 4) on Airfoil differed by up to 0.97 between identical calls). Every
# no-argument `default_rng()` is made deterministic here, so a run is reproducible and the dependence check below
# compares like with like. The choice among tied cells stays arbitrary, just fixed.
_default_rng = np.random.default_rng


def _seeded_default_rng(*args, **kwargs):
    return _default_rng(0) if not args and not kwargs else _default_rng(*args, **kwargs)


np.random.default_rng = _seeded_default_rng

N_ESTIMATORS = 100
TEST_FRACTION = 0.3
CHECK_ROWS = 40  # rows per component in the dependence check


# ── data ─────────────────────────────────────────────────────────────────────────────────────────────


def analytical(seed: int, data_dir: Path, rho: float = 0.5):
    """The paper's analytical case; `rho` is the pairwise correlation of the six inputs (the paper uses 1/2)."""
    rng = default_rng(seed)
    dim, n = 6, 5000
    cov = np.full((dim, dim), rho)
    np.fill_diagonal(cov, 1.0)

    def draw():
        X = rng.multivariate_normal(np.zeros(dim), cov, size=n)
        return X, np.sin(2 * np.pi * X[:, 0]) + X[:, 0] * X[:, 1] + X[:, 2] * X[:, 3] + rng.normal(0, 0.5, n)

    (X, y), (X_test, _) = draw(), draw()
    return X, y, X_test


def airfoil(seed: int, data_dir: Path):
    data = np.loadtxt(data_dir / "airfoil_self_noise.dat")
    X, y = data[:, :5], data[:, 5]
    idx = default_rng(seed).permutation(len(X))
    cut = int(len(X) * (1 - TEST_FRACTION))
    return X[idx[:cut]], y[idx[:cut]], X[idx[cut:]]


DATASETS = {
    "analytical": analytical,
    "airfoil": airfoil,
    # the same function and noise at other pairwise correlations (registered as extension datasets, 2026-10-03)
    "uncorrelated": lambda seed, data_dir: analytical(seed, data_dir, rho=0.0),
    "correlated95": lambda seed, data_dir: analytical(seed, data_dir, rho=0.95),
}


# ── methods ──────────────────────────────────────────────────────────────────────────────────────────


def baseline(model, X_train, X_test):
    """The parent's TreeHFD, order 2, through its public API."""
    hfd = XGBTreeHFD(model)
    hfd.fit(X_train, interaction_order=2, verbose=False)
    y_main, y_order2 = hfd.predict(X_test, verbose=False)
    comps = {(j,): y_main[:, j] for j in range(y_main.shape[1])}
    for k, (a, b) in enumerate(hfd.interaction_list):
        comps[(int(a), int(b))] = y_order2[:, k]
    return float(hfd.eta0), comps


def load_method(spec: str):
    if spec == "baseline":
        return baseline
    module_spec = importlib.util.spec_from_file_location("loop_method", spec)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.decompose


# ── checks and metrics ───────────────────────────────────────────────────────────────────────────────


def mixed_rows(X: np.ndarray, variables: tuple[int, ...], rng) -> np.ndarray:
    """CHECK_ROWS rows whose `variables` match rows 0..CHECK_ROWS-1 of X and whose other variables come from other
    rows."""
    rows = X[:CHECK_ROWS].copy()
    donors = rng.integers(0, len(X), size=len(rows))
    keep = np.zeros(X.shape[1], dtype=bool)
    keep[list(variables)] = True
    rows[:, ~keep] = X[donors][:, ~keep]
    return rows


def run_method(method, model, X_train, X_test, seed: int):
    """(eta0, components on [X_test; X_train], runtime_s, validity message or None).

    The method is called on the held-out rows followed by the training rows, so one fit gives both the held-out and
    the in-sample residual."""
    X_eval = np.vstack([X_test, X_train])
    n = len(X_eval)
    rng = default_rng(seed + 1000)
    t0 = time.perf_counter()
    eta0, comps = method(model, X_train, X_eval)  # components needed to know which sets to check
    runtime = time.perf_counter() - t0
    problems = validate_shape(eta0, comps, n, X_eval.shape[1])
    if problems:
        return eta0, comps, runtime, problems
    keys = sorted(comps)
    blocks = [mixed_rows(X_eval, k, rng) for k in keys]
    _, ext = method(model, X_train, np.vstack([X_eval, *blocks]))
    for i, k in enumerate(keys):
        base = np.asarray(comps[k])[:CHECK_ROWS]
        mixed = np.asarray(ext[k])[n + i * CHECK_ROWS : n + (i + 1) * CHECK_ROWS]
        scale = max(float(np.abs(base).max()), 1e-12)
        if not np.allclose(base, mixed, rtol=1e-5, atol=1e-7 * scale):
            return eta0, comps, runtime, f"component {k} depends on variables outside {k}"
    return eta0, comps, runtime, None


def validate_shape(eta0, comps, n: int, p: int) -> str | None:
    if not isinstance(comps, dict) or not comps:
        return "components must be a non-empty dict {tuple_of_variable_indices: array}"
    for k, v in comps.items():
        if not (isinstance(k, tuple) and k and all(isinstance(i, int) and 0 <= i < p for i in k)):
            return f"bad component key {k!r}"
        if len(k) > 2:
            return f"component {k} has order > 2"
        v = np.asarray(v)
        if v.shape != (n,) or not np.all(np.isfinite(v)):
            return f"component {k} must be a finite array of length {n}"
    if not np.isfinite(float(eta0)):
        return "eta0 is not finite"
    return None


def residual_pct(pred: np.ndarray, hfd: np.ndarray) -> float:
    return float(100 * np.mean((pred - hfd) ** 2) / np.var(pred))


def summary(values: list[float]) -> dict:
    return {"mean": float(np.mean(values)), "std": float(np.std(values)), "values": [float(v) for v in values]}


def evaluate(method, name: str, seeds: int, data_dir: Path) -> dict:
    held_out, in_sample, runtimes, invalid = [], [], [], None
    for seed in range(seeds):
        X, y, X_test = DATASETS[name](seed, data_dir)
        model = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, n_jobs=2, random_state=seed).fit(X, y)
        eta0, comps, runtime, bad = run_method(method, model, X, X_test, seed)
        if bad:
            invalid = bad
            break
        pred = model.predict(np.vstack([X_test, X]))
        hfd = eta0 + sum(np.asarray(v) for v in comps.values())
        n_test = len(X_test)
        held_out.append(residual_pct(pred[:n_test], hfd[:n_test]))
        in_sample.append(residual_pct(pred[n_test:], hfd[n_test:]))
        runtimes.append(runtime)
    if invalid:
        return {"valid": False, "invalid_reason": invalid, "n_seeds": seeds}
    return {"valid": True, "invalid_reason": None, "n_seeds": seeds, "residual_mse_pct": summary(held_out),
            "residual_in_sample_pct": summary(in_sample), "runtime_s": summary(runtimes)}  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="baseline")
    ap.add_argument("--out", default="/work/result.json")
    ap.add_argument("--datasets", default="analytical,airfoil")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--data-dir", default="/work/data")
    ap.add_argument("--protocol", action="store_true", help="run the registered protocol (protocol.py), not datasets")
    ap.add_argument("--protocol-datasets", default="analytical@0.5", help="comma list: analytical@<rho>, airfoil")
    ap.add_argument("--boot", type=int, default=5, help="bootstrap refits per data draw (protocol)")
    args = ap.parse_args(argv)
    if args.protocol:
        from protocol import REFERENCE_METHODS, run_protocol

        names = args.method.split(",")
        methods = {m: REFERENCE_METHODS[m] if m in REFERENCE_METHODS else load_method(m) for m in names}
        out = {"protocol": True, "n_estimators": N_ESTIMATORS, "seeds": args.seeds, "boot": args.boot,
               "results": run_protocol(methods, args.protocol_datasets.split(","), args.seeds, args.boot,
                                       Path(args.data_dir))}  # fmt: skip
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(json.dumps(out)[:2000])
        return
    out: dict = {"method": args.method, "n_estimators": N_ESTIMATORS, "datasets": {}}
    try:
        method = load_method(args.method)
        for name in args.datasets.split(","):
            out["datasets"][name] = evaluate(method, name, args.seeds, Path(args.data_dir))
    except Exception:  # the method's own error: reported, not raised, so the loop can retry with the message
        out["error"] = traceback.format_exc()[-1500:]
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out)[:2000])


if __name__ == "__main__":
    main()
