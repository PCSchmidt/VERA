# ruff: noqa: E501
"""Record the credal baseline reproduction (Increment 4, problem2_ready) against the registered target.

Reads runs/credal-baseline-1/result.json (the by-hand harness's baseline run, the parent's own experiment), evaluates it
with the same rule the loop's baseline gate uses (`vera.loop.credal.baseline_reproduced`: every LV mean within the registered
relative tolerance of the paper's Table 3, and LV best of the five methods on all four metrics), and writes:

  data/results/credal_baseline_1.json   the result, the comparison with Table 3 and the registered tolerance, and the timeline
                                        of the attempts (each failed attempt and what it exposed)
  docs/results/problem2_baseline.md     the same, readable, with the deviations from the parent's environment

The attempts are written here from the session's own record (timestamps from the run directories and the shell log).

Usage: uv run python scripts/record_credal_baseline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from vera.loop import credal, problem, questions, tables

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "credal-baseline-1"
TARGET = ROOT / "docs" / "results" / "credal_baseline_target.json"
ATTEMPTS = [
    ("2026-10-04T13:41:11Z", "setup-lv failed", "the package does not install its SLURM template, which `setup-lv` reads next to main.py: copied into the image"),
    ("2026-10-04T13:52:16Z", "batch failed", "numpy 2.4 raises on the parent's `np.sum(<generator>)`: numpy pinned below 2.3"),
    ("2026-10-04T14:02:27Z", "batch failed", "cvxpy 1.9 no longer has `cp.settings.PARAM_THRESHOLD`: cvxpy pinned below 1.8"),
    ("2026-10-04T14:12:03Z", "batch failed", "Geo-block CV 'no finite fold scores': the parent passes MOSEK-only options (`mosek_params`) that Clarabel rejects, and its cross-validation swallows the error: the options are dropped"),
    ("2026-10-04T14:22:44Z", "batch failed", "the same symptom from a second MOSEK-only option (`accept_unknown`): found by wrapping `Problem.solve` to print the swallowed error; dropped"),
    ("2026-10-04T14:47:10Z", "batch failed after about 6 minutes", "`cannot pickle 'DefaultSolver'`: a solved cvxpy problem holding a Clarabel solver is sent to joblib workers; the solver cache is cleared first"),
    ("2026-10-04T15:06:46Z", "batch completed (5/5 configurations, 100 replications each, about 19 minutes on 8 CPUs)", "the parent's `csv` step then ran over an hour at 100% CPU on five 13 MB files and was stopped at 16:23Z; the harness joins the per-configuration files itself"),
    ("2026-10-04T16:24:11Z", "result read from the finished batch (`--reuse`)", "the baseline run of record"),
]


def main() -> None:
    result = json.loads((RUN / "result.json").read_text(encoding="utf-8"))
    if "error" in result:
        raise SystemExit(f"the baseline run has an error: {result['error'][-300:]}")
    cell = result["datasets"]["california_housing"]
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    with problem.using(credal.CREDAL):
        _, material, shadow = questions.baseline_reproduced(
            target, {tables.BASELINE: result["datasets"]}, 100, ["california_housing"]
        )
    ref, tol = target["reference"], target["tolerance"]["relative"]
    rows = []
    for key, name in credal.REPRO:
        mean, sd = cell[key]["mean"], cell[key]["std"]
        want_mean, want_sd = ref["lv"][key]
        rows.append({"metric": key, "name": name, "mean": round(mean, 3), "sd": round(sd, 3), "paper_mean": want_mean,
                     "paper_sd": want_sd, "relative_difference": round((mean - want_mean) / want_mean, 4),
                     "within_tolerance": abs(mean - want_mean) <= tol * want_mean})  # fmt: skip
    others = {}
    for m, c in cell["reference_methods"].items():
        others[m] = {k: {"mean": round(c[k]["mean"], 3), "paper_mean": ref[m][k][0]} for k, _ in credal.REPRO}
        others[m]["runtime_s"] = round(c["runtime_s"]["mean"], 2)
    lv_best = all(cell[k]["mean"] <= min(c[k]["mean"] for c in cell["reference_methods"].values()) for k, _ in credal.REPRO)
    out = {"run": "credal-baseline-1", "target_sha256": (ROOT / "docs" / "results" / "credal_baseline_target.sha256").read_text().split()[0],
           "image": credal.IMAGE, "n_replications": cell["n"], "lv": rows, "lv_runtime_s": round(cell["runtime_s"]["mean"], 2),
           "other_methods": others, "lv_best_on_all_four": lv_best, "all_within_tolerance": all(r["within_tolerance"] for r in rows),
           "gate_rule_shadow": shadow, "first_attempt_started": ATTEMPTS[0][0], "run_of_record_started": ATTEMPTS[-2][0],
           "attempts": [{"started": a, "outcome": o, "found": f} for a, o, f in ATTEMPTS]}  # fmt: skip
    (ROOT / "data" / "results" / "credal_baseline_1.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = ["# Second problem: the baseline reproduction (2026-10-04)\n\n",
             "The parent's experiment (Chen et al., arXiv 2601.21324, Section 5.2) run through the parent's own tool in "
             f"`{credal.IMAGE}` (the repository at commit 506c17fc, MOSEK replaced by Clarabel), 100 replications per method, "
             f"against the target registered 2026-10-04T13:30:14Z (sha256 `{out['target_sha256'][:12]}`) before any run. Units of 1e4.\n\n",
             "| LV | this run mean (SD) | paper Table 3 mean (SD) | relative difference | within 5% |\n|---|---|---|---|---|\n"]  # fmt: skip
    for r in rows:
        lines.append(f"| {r['name']} | {r['mean']} ({r['sd']}) | {r['paper_mean']} ({r['paper_sd']}) | {r['relative_difference']:+.1%} | {'yes' if r['within_tolerance'] else 'NO'} |\n")
    lines.append(f"\nLV is best of the five methods on all four metrics: {'yes' if lv_best else 'NO'}. The loop's baseline-gate rule says: {'accept' if shadow else 'reject'}.\n\n")
    lines.append("| Method | MAE (paper) | RMSE (paper) | p98 (paper) | CVaR 2% (paper) | seconds per replication |\n|---|---|---|---|---|---|\n")
    for m, v in others.items():
        lines.append(f"| {m} | " + " | ".join(f"{v[k]['mean']} ({v[k]['paper_mean']})" for k, _ in credal.REPRO) + f" | {v['runtime_s']} |\n")
    lines.append(f"\nLV: {out['lv_runtime_s']} s per replication (the paper's Table 4: 1.44 for LV, 5.47 for CVaR, 6.16 for Wasserstein, on MOSEK and another machine; "
                 "times are reported, never gated). Wasserstein's MAE differs from the paper's by about 4%: inside the registered 5% for LV, "
                 "which is the row the gate reads, and reported for the others.\n\n## What it took\n\n")
    for a, o, f in ATTEMPTS:
        lines.append(f"- {a}: {o}. {f}.\n")
    lines.append("\nEach failure exposed a way the parent's repository does not run as published in a fresh environment: its dependencies are not "
                 "pinned (`numpy>=1.26.2`, `cvxpy>=1.4.2`), it leans on a solver whose licence is personal, and it hides solver errors. "
                 "The changes are in `docker/sandbox-credal/` (Dockerfile and `patch_solver.py`); the clone is not committed (the repository has no licence file).\n")
    (ROOT / "docs" / "results" / "problem2_baseline.md").write_text("".join(lines), encoding="utf-8")
    print(json.dumps({"within": out["all_within_tolerance"], "lv_best": lv_best, "shadow": shadow}))


if __name__ == "__main__":
    main()
