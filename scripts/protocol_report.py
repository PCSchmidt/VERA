# ruff: noqa: E501
"""Render the registered protocol's results and score its pre-registered expectations (Increment 4).

Reads data/results/protocol_<tag>.json and docs/results/tree_explain_protocol.json (the registered target, whose
`expectations_written_before_any_run` list is what is scored) and writes docs/results/tree_explain_protocol_results.md:
the tables VERA renders for the write-up, then each expectation with the numbers it was decided on and whether it held.
An expectation that failed is reported as failed.

Usage: uv run python scripts/protocol_report.py --tag tree-explain-1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vera.loop import tables

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"treehfd": "TreeHFD", "treeshap": "TreeSHAP"}


def merged(tag: str) -> tuple[dict, dict, list[str]]:
    """The run's cells: data/results/protocol_<tag>.json, and any later `protocol_<tag>-*.json` re-run cells laid over
    it (a cell re-run after a harness bug fix replaces the first). Returns (first file's header, results, replaced)."""
    files = sorted((ROOT / "data" / "results").glob(f"protocol_{tag}*.json"), key=lambda p: (len(p.name), p.name))
    first = json.loads(files[0].read_text(encoding="utf-8"))
    results = {m: dict(cells) for m, cells in first["results"].items()}
    replaced = []
    for f in files[1:]:
        extra = json.loads(f.read_text(encoding="utf-8"))
        if extra["target_sha256"] != first["target_sha256"]:
            raise SystemExit(f"{f.name} was not made under the registered target")
        for m, cells in extra["results"].items():
            for d, cell in cells.items():
                if d in results[m]:
                    replaced.append(f"{m} on {d} (from {f.name})")
                results[m][d] = cell
    return first, results, replaced


def mean(cell: dict, key: str) -> float | None:
    v = cell.get(key) if cell.get("valid") else None
    return None if v is None else v["mean"]


def expectations(results: dict, datasets: list[str]) -> list[dict]:
    analytical = sorted((d for d in datasets if d.startswith("analytical@")), key=lambda d: float(d.split("@")[1]))
    hfd, shap = results["treehfd"], results["treeshap"]
    out = []
    pairs = [(d, mean(hfd[d], "component_mse_pct"), mean(shap[d], "component_mse_pct")) for d in analytical]
    out.append({"id": "E1", "held": all(a is not None and b is not None and a < b for _, a, b in pairs),
                "evidence": "; ".join(f"{d.split('@')[1]}: TreeHFD {a:.3g} vs TreeSHAP {b:.3g}" for d, a, b in pairs
                                      if a is not None and b is not None)})  # fmt: skip
    for tag, cells in (("TreeHFD", hfd), ("TreeSHAP", shap)):
        lo, hi = mean(cells[analytical[0]], "component_mse_pct"), mean(cells[analytical[-1]], "component_mse_pct")
        out.append({"id": f"E2 ({tag})", "held": lo is not None and hi is not None and hi > lo,
                    "evidence": f"rho {analytical[0].split('@')[1]}: {lo}; rho {analytical[-1].split('@')[1]}: {hi}"})
    stab = [(d, mean(hfd[d], "rank_stability")) for d in analytical]
    out.append({"id": "E3", "held": all(s is not None and s >= 0.8 for _, s in stab),
                "evidence": "; ".join(f"{d.split('@')[1]}: {s:.3g}" for d, s in stab if s is not None)})  # fmt: skip
    fails = {d: hfd_cell for d, hfd_cell in shap.items() if hfd_cell.get("valid") and hfd_cell.get("own_variables_only")}
    out.append({"id": "E4", "held": not fails,
                "evidence": "TreeSHAP own_variables_only: " + ", ".join(f"{d}={c.get('own_variables_only')}"
                                                                         for d, c in shap.items())})  # fmt: skip
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    data, results, replaced = merged(args.tag)
    target = json.loads((ROOT / "docs" / "results" / "tree_explain_protocol.json").read_text(encoding="utf-8"))
    protocol = {"datasets": target["datasets"], "methods": [LABEL[m] for m in results], "n_seeds": data["seeds"],
                "n_boot": data["boot"], "results": {LABEL[m]: cells for m, cells in results.items()}}  # fmt: skip
    scored = expectations(results, target["datasets"])
    texts = target["expectations_written_before_any_run"]
    note = ("Cells re-run after a harness bug fix (TreeSHAP's component keys assumed six variables, so its Airfoil run was "
            "invalid) replace the first run's: " + "; ".join(replaced) + ".\n\n") if replaced else ""
    lines = [f"# Tree-explain protocol: results ({args.tag})\n\n",
             f"Registered {target['registered']} (target sha256 `{data['target_sha256'][:12]}`), image `{data['image']}`. "
             "No value here is a figure from ScientistTwo's paper.\n\n" + note, tables.render_protocol(protocol),
             "\n\n## The expectations written down before any run\n\n"]  # fmt: skip
    for e in scored:
        base = next((t for t in texts if t.startswith(e["id"].split(" ")[0] + ":")), "")
        lines.append(f"- **{e['id']}: {'held' if e['held'] else 'did NOT hold'}.** {base}\n  - {e['evidence']}\n")
    out = ROOT / "docs" / "results" / "tree_explain_protocol_results.md"
    out.write_text("".join(lines), encoding="utf-8")
    print("".join(lines))


if __name__ == "__main__":
    main()
