# ruff: noqa: E501  (registered prose is kept as written)
"""Register the tree-explain protocol (Increment 4, protocol_ready) before any protocol run.

Writes, once:
  docs/results/tree_explain_protocol.json        the target file: question, methods, datasets, metrics, the primary
                                                 metric, seeds, bootstrap refits, and the expectations written down
                                                 before any run (including what would count as a failed expectation)
  docs/results/tree_explain_protocol_spec.json   a `ProtocolSpec` naming that file and its SHA-256
  docs/results/table3_check.json                 the closed-form truth against the TreeHFD paper's Table 3, per rho

Refuses to run if any protocol result exists (data/results/protocol_*.json): the registration comes first.

Usage: uv run python scripts/register_protocol.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docker" / "sandbox-treehfd"))
import truth  # noqa: E402

from vera.schemas import ProtocolSpec  # noqa: E402

RHOS = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95]
QUESTION = (
    "How does TreeHFD's decomposition compare with TreeSHAP's, and with the true components, on the analytical case "
    "as the pairwise correlation of the inputs rises from 0 to 0.95, and how stable are the component importances "
    "under bootstrap refits of the ensemble?"
)


def main() -> None:
    results = list((ROOT / "data" / "results").glob("protocol_*.json"))
    if results:
        raise SystemExit(f"protocol results exist ({results[0].name}): the registration must come first")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    check = [truth.table3_check(r) for r in RHOS]
    worst = max(c["max_relative_difference"] for c in check)
    if worst >= 0.01:
        raise SystemExit(f"the closed-form truth differs from Table 3 by {worst:.2%}: no method may be scored")
    (ROOT / "docs" / "results" / "table3_check.json").write_text(
        json.dumps({"checked": now, "tolerance": 0.01, "worst_relative_difference": worst, "per_rho": check},
                   indent=1), encoding="utf-8")  # fmt: skip
    target = {
        "registered": now,
        "note": "Written before any protocol run. Changing anything below after the first run needs Chris's approval and "
                "a dated entry in 'changes'. No value here is a figure from ScientistTwo's paper.",  # fmt: skip
        "question": QUESTION,
        "methods": {
            "treehfd": "the parent's TreeHFD, interaction order 2 (harness.baseline)",
            "treeshap": "xgboost's TreeSHAP with interaction values, path-dependent: main effects from the diagonal, pairs "
                        "from the two off-diagonal entries (protocol.treeshap)",
            "ideas": "each idea of the run that survives the loop's screen, on the same cells",
        },  # fmt: skip
        "datasets": [f"analytical@{r:g}" for r in RHOS] + ["airfoil"],
        "dataset_notes": {
            "analytical@rho": "the paper's analytical case (Section 4) with pairwise correlation rho; the true HFD is "
                              "closed-form (docker/sandbox-treehfd/truth.py), checked against the paper's Table 3 first "
                              "(docs/results/table3_check.json)",
            "airfoil": "the registered public dataset: no true components exist, so only the residual, the rank "
                       "stability and the runtime are computed",
        },  # fmt: skip
        "metrics": {
            "component_mse_pct": "sum over components of the mean squared difference from the true component on held-out "
                                 "rows, as a percentage of the variance of the true signal (analytical only); lower is better",
            "component_mse": "the same sum, not scaled",
            "residual_mse_pct": "the method's components against the fitted ensemble, as in the baseline target",
            "rank_stability": "mean Spearman correlation of component importances (variance over fixed held-out rows) "
                              "across all pairs of bootstrap refits; 1 is the same ranking every time",
            "rank_vs_truth": "Spearman correlation of the method's importances with the true components' (analytical only)",
            "runtime_s": "seconds for the decomposition call",
            "own_variables_only": "whether every component is a function of its own variables alone; enforced for TreeHFD "
                                  "and ideas, reported for TreeSHAP",
        },  # fmt: skip
        "primary_metric": "component_mse_pct",
        "n_seeds": 3,
        "n_boot": 5,
        "expectations_written_before_any_run": [
            "E1: TreeHFD's component_mse_pct is below TreeSHAP's at every analytical correlation (the paper's claim that "
            "TreeHFD targets the HFD and TreeSHAP a different decomposition). Failed if TreeSHAP is lower at any rho.",
            "E2: both methods' component_mse_pct rises with rho (the dependence makes the targets harder to separate). "
            "Failed if the value at 0.95 is not above the value at 0.",
            "E3: TreeHFD's rank_stability is at least 0.8 at every rho. Failed if any is below.",
            "E4: TreeSHAP's decomposition fails the own-variables-only check (its attributions depend on the whole row). "
            "Failed if it passes.",
        ],  # fmt: skip
        "changes": [],
    }
    path = ROOT / "docs" / "results" / "tree_explain_protocol.json"
    path.write_text(json.dumps(target, indent=1), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    spec = ProtocolSpec(
        id="tree-explain-1", question=QUESTION, methods=["treehfd", "treeshap"], datasets=target["datasets"],
        metrics=list(target["metrics"]), primary_metric="component_mse_pct", n_seeds=3,
        target_file="docs/results/tree_explain_protocol.json", target_sha256=digest,
    )  # fmt: skip
    (ROOT / "docs" / "results" / "tree_explain_protocol_spec.json").write_text(
        spec.model_dump_json(indent=1), encoding="utf-8")
    print(f"registered {now}; Table 3 worst relative difference {worst:.2e}; target sha256 {digest[:12]}")


if __name__ == "__main__":
    main()
