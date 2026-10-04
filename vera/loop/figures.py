# ruff: noqa: E501
"""Figures for the paper-shaped write-up (Increment 4): drawn by VERA from `results.json`, never by the model.

`plan` decides which figures a run's results support, each as a `FigureSpec` naming the cells it shows (a cell is
`<table>/<method>/<dataset>/<metric>`, the table being `results` for the loop's table or `protocol` for the registered
protocol's). `series` reads the plotted numbers from those cells; `draw` plots them with a fixed style (matplotlib, Agg)
and writes the data it plotted next to the image, so the audit can check that a figure's data equal its source cells: a
figure drawn from other numbers fails. The model writes the caption and the prose that refers to the figure.

Figures: for the protocol, the error against the true components and the rank stability as the correlation rises; for the
loop's table, the primary metric per method and dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

from vera.loop import tables
from vera.schemas import FigureSpec

MAX_BAR_DATASETS = 8
STYLE = {"figure.figsize": (6.4, 3.6), "font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
         "axes.spines.right": False}  # fmt: skip


def cell_id(table: str, method: str, dataset: str, metric: str) -> str:
    return f"{table}/{method}/{dataset}/{metric}"


def cell_value(results_json: dict, cell: str) -> dict | None:
    """The {mean, std} the cell names in results.json, or None if it does not exist (or is invalid)."""
    table, method, dataset, metric = cell.split("/")
    root = results_json.get("protocol") if table == "protocol" else {"results": results_json["results"]}
    if not root:
        return None
    entry = (root["results"].get(method) or {}).get(dataset) or {}
    value = entry.get(metric)
    return value if isinstance(value, dict) and entry.get("valid", True) else None


def rho_of(dataset: str) -> float | None:
    return float(dataset.split("@")[1]) if dataset.startswith("analytical@") else None


def plan(results_json: dict) -> list[dict]:
    """The figures this run's results support: [{"spec": FigureSpec (caption blank), "title", "xlabel", "ylabel"}]."""
    out: list[dict] = []
    protocol = results_json.get("protocol")
    if protocol:
        rhos = sorted((rho_of(d), d) for d in protocol["datasets"] if rho_of(d) is not None)
        for key, title, ylabel in (("component_mse_pct", "Component error against the true decomposition", "% of signal variance"),
                                   ("rank_stability", "Rank stability of component importances", "Spearman across refits")):  # fmt: skip
            cells = [cell_id("protocol", m, d, key) for m in protocol["methods"] for _, d in rhos
                     if cell_value(results_json, cell_id("protocol", m, d, key))]  # fmt: skip
            if cells:
                spec = FigureSpec(id=f"fig_{key}", kind="line", cells=cells, caption="(to be written)")
                out.append({"spec": spec, "title": title, "xlabel": "pairwise correlation of the inputs", "ylabel": ylabel})
    names = tables.METRIC_NAME
    primary = tables.PRIMARY
    datasets = tables.valid_datasets(results_json["results"], results_json["datasets"])[:MAX_BAR_DATASETS]
    cells = [cell_id("results", m, d, primary) for m in results_json["results"] for d in datasets]
    if datasets and all(cell_value(results_json, c) for c in cells):
        spec = FigureSpec(id=f"fig_{primary}", kind="bar", cells=cells, caption="(to be written)")
        out.append({"spec": spec, "title": f"{names.get(primary, primary)} by method and dataset (held-out)",
                    "xlabel": "dataset", "ylabel": names.get(primary, primary)})  # fmt: skip
    return out


def series(results_json: dict, spec: FigureSpec) -> dict[str, list[dict]]:
    """{method: [{x, mean, std, cell}]} read from the figure's cells, x being the correlation (line) or the dataset."""
    out: dict[str, list[dict]] = {}
    for cell in spec.cells:
        _, method, dataset, _ = cell.split("/")
        value = cell_value(results_json, cell)
        if value is None:
            raise ValueError(f"figure {spec.id} names a cell that is not in results.json: {cell}")
        x = rho_of(dataset) if spec.kind == "line" else dataset
        out.setdefault(method, []).append({"x": x, "mean": value["mean"], "std": value["std"], "cell": cell})
    for points in out.values():
        if spec.kind == "line":
            points.sort(key=lambda p: p["x"])
    return out


def draw(results_json: dict, planned: list[dict], folder: Path) -> list[dict]:
    """Draw each planned figure into `folder` as PNG; returns the records written to `figures.json` (spec, file, the
    plotted data). The data are what the plot was given, read from the cells, not recomputed."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    folder.mkdir(parents=True, exist_ok=True)
    records = []
    with plt.rc_context(STYLE):
        for item in planned:
            spec: FigureSpec = item["spec"]
            data = series(results_json, spec)
            fig, ax = plt.subplots()
            if spec.kind == "line":
                for method, pts in data.items():
                    ax.errorbar([p["x"] for p in pts], [p["mean"] for p in pts], yerr=[p["std"] for p in pts],
                                marker="o", capsize=2, label=method)  # fmt: skip
            else:
                methods = list(data)
                width = 0.8 / max(len(methods), 1)
                for i, method in enumerate(methods):
                    pts = data[method]
                    ax.bar([k + i * width for k in range(len(pts))], [p["mean"] for p in pts],
                           width=width, yerr=[p["std"] for p in pts], capsize=2, label=method)  # fmt: skip
                first = next(iter(data.values()))
                ax.set_xticks([k + 0.4 - width / 2 for k in range(len(first))],
                              [tables.dataset_label(p["x"]) for p in first], rotation=20, ha="right")  # fmt: skip
            ax.set_title(item["title"])
            ax.set_xlabel(item["xlabel"])
            ax.set_ylabel(item["ylabel"])
            ax.legend(fontsize=7)
            fig.tight_layout()
            file = folder / f"{spec.id}.png"
            fig.savefig(file, dpi=150)
            plt.close(fig)
            records.append({"id": spec.id, "kind": spec.kind, "cells": spec.cells, "file": file.name,
                            "title": item["title"], "data": data})  # fmt: skip
    (folder / "figures.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    return records


def check_data(results_json: dict, records: list[dict]) -> list[str]:
    """Problems found comparing each figure's plotted data with the cells it names (empty: they agree)."""
    problems = []
    for rec in records:
        named = set(rec["cells"])
        plotted = {p["cell"]: p for pts in rec["data"].values() for p in pts}
        if set(plotted) != named:
            problems.append(f"{rec['id']}: the plotted cells differ from the cells it names")
        for cell, p in plotted.items():
            value = cell_value(results_json, cell)
            if value is None:
                problems.append(f"{rec['id']}: {cell} is not in results.json")
            elif abs(p["mean"] - value["mean"]) > 1e-9 or abs(p["std"] - value["std"]) > 1e-9:
                problems.append(f"{rec['id']}: {cell} was plotted as {p['mean']:.6g} ± {p['std']:.6g}, results.json has "
                                f"{value['mean']:.6g} ± {value['std']:.6g}")  # fmt: skip
    return problems
