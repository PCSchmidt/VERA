# ruff: noqa: E501
"""Gate `protocol_ready`: the registered protocol experiment, its ground truth and one live run (Increment 4).

Requires:
- docs/results/tree_explain_protocol_spec.json, whose target file exists with the SHA-256 the spec recorded; the target
  registers at least five analytical correlations from 0 to at least 0.95, the metrics (component error, rank stability,
  residual, runtime), a primary metric, and written expectations;
- docs/results/table3_check.json: the closed-form truth within 1% of the TreeHFD paper's Table 3 at five or more
  correlations, checked before the protocol was registered (the target's own `registered` date is not earlier);
- data/results/protocol_<tag>.json: made under that hash, every method x dataset cell present for TreeHFD and TreeSHAP,
  each valid or invalid with a reason, and at least one valid TreeHFD cell at every analytical correlation;
- docs/results/tree_explain_protocol_results.md with every registered expectation (E1 to E4) stated as held or not;
- docs/results/protocol_live_run.json: the loop's own live run on the question (run id, model spend within $1.00, the
  protocol artifact and the paper it wrote, both committed), whose protocol cells are all valid or invalid with a reason.
"""

from __future__ import annotations

import hashlib
import json
import re

from _common import block, ok, repo_root_arg

CAP_USD = 1.00
METRICS = {"component_mse_pct", "rank_stability", "residual_mse_pct", "runtime_s"}


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def check_cells(results: dict, datasets: list[str], methods: list[str], what: str) -> None:
    for m in methods:
        for d in datasets:
            cell = results.get(m, {}).get(d)
            if cell is None:
                block(f"{what}: no cell for {m} on {d}")
            if not cell.get("valid") and not str(cell.get("invalid_reason") or "").strip():
                block(f"{what}: {m} on {d} is invalid without a reason")


def main() -> None:
    parser = repo_root_arg(__doc__)
    args = parser.parse_args()
    res = args.root / "docs" / "results"
    spec = load(res / "tree_explain_protocol_spec.json", "the protocol spec")
    target_path = args.root / spec["target_file"]
    if not target_path.exists():
        block(f"{spec['target_file']} not found")
    if hashlib.sha256(target_path.read_bytes()).hexdigest() != spec["target_sha256"]:
        block("the protocol target file changed after it was registered")
    target = json.loads(target_path.read_text(encoding="utf-8"))
    analytical = sorted(float(d.split("@")[1]) for d in target["datasets"] if d.startswith("analytical@"))
    if len(analytical) < 5 or analytical[0] != 0.0 or analytical[-1] < 0.95:
        block(f"the protocol needs at least five correlations from 0 to 0.95 or more; it has {analytical}")
    if not METRICS <= set(target["metrics"]) or target["primary_metric"] not in target["metrics"]:
        block(f"the protocol's metrics must include {sorted(METRICS)} and a primary metric")
    expectations = target.get("expectations_written_before_any_run") or []
    if not expectations:
        block("the protocol records no expectations written before the run")

    t3 = load(res / "table3_check.json", "the Table 3 check")
    if len(t3["per_rho"]) < 5 or t3["worst_relative_difference"] >= 0.01:
        block("the closed-form truth must match Table 3 within 1% at five or more correlations")
    if t3["checked"] > target["registered"]:
        block("the Table 3 check is dated after the registration: the ground truth comes first")

    runs = sorted((args.root / "data" / "results").glob("protocol_*.json"), key=lambda p: (len(p.name), p.name))
    if not runs:
        block("no data/results/protocol_<tag>.json")
    merged: dict = {}
    for run in runs:  # the first file is the run; a longer-named one holds cells re-run after a bug fix, laid over it
        data = json.loads(run.read_text(encoding="utf-8"))
        if data["target_sha256"] != spec["target_sha256"]:
            block(f"{run.name} was not made under the registered target (hash differs)")
        for m, cells in data["results"].items():
            merged.setdefault(m, {}).update(cells)
    check_cells(merged, target["datasets"], ["treehfd", "treeshap"], "the protocol results")
    for rho in analytical:
        if not merged["treehfd"][f"analytical@{rho:g}"].get("valid"):
            block(f"TreeHFD has no valid cell at analytical correlation {rho:g}")

    report = res / "tree_explain_protocol_results.md"
    if not report.exists():
        block("docs/results/tree_explain_protocol_results.md not found (scripts/protocol_report.py)")
    text = report.read_text(encoding="utf-8")
    for e in ("E1", "E2", "E3", "E4"):
        if not re.search(rf"\*\*{e}\b[^*]*(held|did NOT hold)", text):
            block(f"the results report does not state whether {e} held")

    live = load(res / "protocol_live_run.json", "the live-run record")
    if not live.get("run_id") or float(live.get("spent_usd", 99)) > CAP_USD:
        block(f"the live run needs a run id and model spend within ${CAP_USD:.2f}")
    for key in ("protocol_artifact", "paper"):
        if not (args.root / live.get(key, "missing")).exists():
            block(f"the live run's {key} is not committed ({live.get(key)})")
    artifact = json.loads((args.root / live["protocol_artifact"]).read_text(encoding="utf-8"))
    check_cells(artifact["results"], artifact["datasets"], artifact["methods"], "the live run")
    ok(f"protocol registered ({len(target['datasets'])} datasets, {len(expectations)} expectations); Table 3 within "
       f"{t3['worst_relative_difference']:.1e}; {len(runs)} result file(s) complete; live run {live['run_id']} at ${live['spent_usd']}")


if __name__ == "__main__":
    main()
