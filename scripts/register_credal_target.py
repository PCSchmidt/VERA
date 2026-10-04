# ruff: noqa: E501
"""Register the second parent problem's baseline target (Increment 4, problem2_ready) before any baseline run.

The target comes from the parent paper only (Chen et al., arXiv 2601.21324, Section 5.2, Tables 3 and 4), never from
ScientistTwo's paper on it. Writes docs/results/credal_baseline_target.json with a registration timestamp and
docs/results/credal_baseline_target.sha256 with its hash. Refuses if any baseline result for the problem exists
(data/results/credal_baseline*.json) or the target is already registered.

Usage: uv run python scripts/register_credal_target.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "results" / "credal_baseline_target.json"

TARGET = {
    "note": "Written before any baseline run. Reference values are from the parent paper only (Table 3, Table 4, Section 5.2). "
            "Changing anything below after the first baseline run needs Chris's approval and a dated entry in 'changes'.",
    "parent": {"paper": "arXiv:2601.21324", "repo": "https://github.com/MengqiChenMC/credal-ambiguity-sets-code-repo",
               "commit": "506c17fc28e87619e4532afeff8389083e578557"},
    "problem": "Linear regression with the absolute loss on California Housing under an East-to-West geographic deployment shift "
               "(train and tune on the Eastern 50% of the data, evaluate on the Western 20%, the intermediate 30% band excluded; "
               "paper Section 5.2). The parent's method is LV, the bulk-calibrated credal ambiguity set; the paper compares it with CVaR, "
               "Wasserstein, ridge and ERM baselines.",
    "experiment": {"cli": "credaldro setup-lv lv_california_housing_val", "gap_ratio": 0.30, "n_replications": 100,
                   "n_replications_note": "the paper's 100; the run may use fewer only through a dated entry in 'changes'"},
    "modification": "The repository hard-codes the commercial MOSEK solver in its baselines; the image replaces it by the open solver "
                    "Clarabel (docker/sandbox-credal/patch_solver.py). Values and times can differ from the paper's MOSEK runs, which is why "
                    "the tolerance below is registered first. Chris accepted this on 2026-10-04.",
    "comparison_metric": "mae",
    "metrics": {
        "mae": "test mean absolute error, in units of 1e4 (housing value in dollars / 1e4); the metric ideas are compared on",
        "rmse": "test root mean squared error, units of 1e4",
        "p98_abs_error": "98th percentile of the absolute test error, units of 1e4",
        "cvar_abs_error": "2% tail risk CVaR of the absolute test error, units of 1e4",
    },
    "lower_is_better": True,
    "methods": {"lv": "LV (the parent's method)", "cvar": "CVaR", "wass": "Wasserstein", "ridge": "Ridge", "erm": "ERM"},
    "reference": {
        "source": "paper Table 3, 'Entries are mean (SD) over 100 replications. All error metrics are reported in units of 10^4.'",
        "lv": {"mae": [10.7, 0.72], "rmse": [12.2, 0.77], "p98_abs_error": [21.9, 1.23], "cvar_abs_error": [23.9, 1.10]},
        "cvar": {"mae": [13.0, 0.00], "rmse": [14.4, 0.00], "p98_abs_error": [24.7, 0.00], "cvar_abs_error": [27.2, 0.00]},
        "wass": {"mae": [12.3, 0.02], "rmse": [13.7, 0.02], "p98_abs_error": [24.3, 0.04], "cvar_abs_error": [26.5, 0.03]},
        "ridge": {"mae": [13.2, 0.01], "rmse": [14.6, 0.01], "p98_abs_error": [25.2, 0.01], "cvar_abs_error": [27.7, 0.01]},
        "erm": {"mae": [12.7, 0.00], "rmse": [14.1, 0.00], "p98_abs_error": [24.7, 0.00], "cvar_abs_error": [27.7, 0.00]},
    },
    "runtime_reference_seconds": {
        "source": "paper Table 4, total per replication; machine-dependent, reported and never gated",
        "lv": 1.44, "cvar": 5.47, "wass": 6.16,
    },
    "tolerance": {
        "reproduction": "the LV row of this run's mean for each of the four metrics is within 5% (relative) of the paper's mean for it",
        "relative": 0.05,
        "ordering": "LV has the lowest mean of the five methods on all four metrics, as the paper reports (reported, and a gate "
                    "failure if it does not hold: the paper's claim is then not reproduced)",
        "sd": "not gated; reported beside the paper's",
    },
    "validity_checks": [
        "every replication's metrics are finite",
        "the number of replications per method is the registered number",
        "the five methods are all present",
        "an idea's predictions depend only on the training rows and the evaluated rows' features (never the test labels)",
    ],
    "changes": [],
}


def main() -> None:
    if OUT.exists():
        raise SystemExit("the credal target is already registered")
    if list((ROOT / "data" / "results").glob("credal_baseline*.json")):
        raise SystemExit("a credal baseline result exists: the target must be registered first")
    TARGET["registered"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(TARGET, indent=1), encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    OUT.with_suffix(".sha256").write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    print(f"registered {TARGET['registered']} sha256 {digest[:12]}")


if __name__ == "__main__":
    main()
