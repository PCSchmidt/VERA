# ruff: noqa: E501
"""The thin generic harness (T10 option (c), Increment 4): what a harness needs for any parent problem, with the parent-specific
part left to a model-written adapter. Runs INSIDE the sandbox; written by VERA, not by the model.

It does the generic work the by-hand harness (`harness.py`) also does: it loads the adapter, runs it, checks the numbers it
returns (every registered method present, the registered number of replications, every value finite), summarises them
(mean, spread, values) and writes `result.json` in the shape the loop's baseline gate reads. The adapter is the part that
knows the parent's code:

    def run(data_dir: str, work_dir: str, n_replications: int) -> dict:
        '''{method: {metric: [one value per replication]}} for the methods "lv", "cvar", "wass", "ridge", "erm" and the
        metrics "mae", "rmse", "p98_abs_error", "cvar_abs_error" (units of 1e4) and "runtime_s" (seconds)'''

Usage (in the container): python generic_harness.py --adapter /work/adapter.py --seeds 100 --out /work/result.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import traceback
from pathlib import Path

import numpy as np

METHODS = ("lv", "cvar", "wass", "ridge", "erm")
METRICS = ("mae", "rmse", "p98_abs_error", "cvar_abs_error")


def summary(values: list[float]) -> dict:
    return {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "values": [float(v) for v in values]}  # fmt: skip


def load_adapter(path: str):
    spec = importlib.util.spec_from_file_location("adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def cell_of(raw: dict, n_expected: int) -> dict:
    """One method's result cell from the adapter's lists, with the validity checks."""
    problems = []
    for m in (*METRICS, "runtime_s"):
        values = raw.get(m)
        if values is None:
            problems.append(f"no values for {m}")
        elif len(values) != n_expected:
            problems.append(f"{len(values)} values for {m}, the registered number of replications is {n_expected}")
        elif not np.all(np.isfinite(np.asarray(values, dtype=float))):
            problems.append(f"a value of {m} is not finite")
    if problems:
        return {"valid": False, "invalid_reason": "; ".join(problems)}
    return {"valid": True, "n": n_expected, **{m: summary(raw[m]) for m in (*METRICS, "runtime_s")}}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", default="/work/result.json")
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--data-dir", default="/work/data")
    args = ap.parse_args(argv)
    out: dict = {"method": "baseline", "datasets": {}}
    try:
        raw = load_adapter(args.adapter)(args.data_dir, str(Path(args.out).parent), args.seeds)
        missing = [m for m in METHODS if m not in raw]
        if missing:
            raise ValueError(f"the adapter returned no results for {missing}")
        cells = {m: cell_of(raw[m], args.seeds) for m in METHODS}
        out["datasets"]["california_housing"] = {**cells["lv"], "n_seeds": args.seeds,
                                                 "reference_methods": {m: c for m, c in cells.items() if m != "lv"}}  # fmt: skip
    except Exception:  # the adapter's own error: reported, not raised
        out["error"] = traceback.format_exc()[-1500:]
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out)[:2000])


if __name__ == "__main__":
    main()
