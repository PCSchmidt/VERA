"""Result tables for the loop's gates, in the form the Increment 1 benchmark measured the judge on.

`render_results` writes the same markdown layout as `vera.bench.build.result_table` ("Method" rows, one column per
dataset and metric, `mean ± std`, an arrow for the direction). The shadow answers (`beats`, `best`) are computed from
the numbers as *rendered*, to the same significant figures, because that is all a judge can read: a gap that
rounds away is a tie, for the judge and for the shadow label alike.
"""

from __future__ import annotations

BASELINE = "TreeHFD (baseline)"
METRICS: tuple[tuple[str, str], ...] = (("residual_mse_pct", "Residual MSE (%)"), ("runtime_s", "Runtime (s)"))
PRIMARY = "residual_mse_pct"  # held-out: what ideas are compared on
# The baseline-reproduction gate checks the in-sample residual against the paper (docs/results target, `changes`)
REPRO_METRIC = "residual_in_sample_pct"
REPRO_METRICS: tuple[tuple[str, str], ...] = (
    (REPRO_METRIC, "Residual MSE, in-sample (%)"),
    (PRIMARY, "Residual MSE, held-out (%)"),
)
METRIC_NAME = dict(METRICS)  # the names the benchmark-format tables use; all metrics are lower-is-better
SIG = 3
PROBLEM_NAME = "TreeHFD"  # set by vera.loop.problem.use: the parent problem the tables describe


def fmt_sig(x: float, sig: int = SIG) -> str:
    """x to `sig` significant figures, fixed-point (no exponent), keeping trailing zeros."""
    if x == 0:
        return "0"
    digits = max(sig - 1 - int(f"{abs(x):e}".split("e")[1]), 0)
    return f"{x:.{digits}f}"


def dataset_label(name: str) -> str:
    return name.replace("_", " ").capitalize()


def valid_datasets(results: dict[str, dict], datasets: list[str]) -> list[str]:
    """Datasets on which every method in `results` has a valid result."""
    return [d for d in datasets if all(res.get(d, {}).get("valid") for res in results.values())]


def render_results(
    results: dict[str, dict], datasets: list[str], n_seeds: int, metrics: tuple[tuple[str, str], ...] | None = None
) -> str:
    """`results`: method name -> the harness's per-dataset results. Only datasets valid for every method appear."""
    metrics = metrics or METRICS
    shown = valid_datasets(results, datasets)
    columns = [(d, key) for d in shown for key, _ in metrics]
    names = dict(metrics)
    header = ["Method"] + [f"{dataset_label(d)} · {names[k]} ↓" for d, k in columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for method, res in results.items():
        cells = [f"{fmt_sig(res[d][k]['mean'])} ± {fmt_sig(res[d][k]['std'], 2)}" for d, k in columns]
        lines.append("| " + " | ".join([method, *cells]) + " |")
    return (
        f"Results from a research-loop run on the {PROBLEM_NAME} problem (mean ± std over {n_seeds} seeds). "
        "↓ = lower is better; ↑ = higher is better.\n\n" + "\n".join(lines)
    )


def rendered_means(
    results: dict[str, dict], datasets: list[str], metrics: tuple[tuple[str, str], ...] | None = None
) -> dict[tuple[str, str, str], float]:
    """(method, dataset, metric key) -> the mean as the table shows it."""
    metrics = metrics or METRICS
    out = {}
    for method, res in results.items():
        for d in valid_datasets(results, datasets):
            for key, _ in metrics:
                out[(method, d, key)] = float(fmt_sig(res[d][key]["mean"]))
    return out


def beats(means: dict, method: str, dataset: str, metric: str = PRIMARY) -> bool:
    """Strictly better (lower) rendered mean than the baseline's."""
    return means[(method, dataset, metric)] < means[(BASELINE, dataset, metric)]


def best(means: dict, methods: list[str], dataset: str, metric: str = PRIMARY) -> str | None:
    """The method with the lowest rendered mean, or None if the best is tied."""
    values = {m: means[(m, dataset, metric)] for m in methods}
    low = min(values.values())
    winners = [m for m, v in values.items() if v == low]
    return winners[0] if len(winners) == 1 else None


# ── the registered protocol's tables (Increment 4) ───────────────────────────────────────────────────

PROTOCOL_METRICS: tuple[tuple[str, str, str], ...] = (  # (key, title, arrow)
    ("component_mse_pct", "Component error against the true decomposition (% of signal variance)", "↓"),
    ("rank_stability", "Rank stability of component importances across bootstrap refits (Spearman)", "↑"),
    ("rank_vs_truth", "Rank agreement of component importances with the true ones (Spearman)", "↑"),
    ("residual_mse_pct", "Residual MSE against the fitted ensemble (%)", "↓"),
    ("runtime_s", "Runtime of the decomposition call (s)", "↓"),
)


def protocol_dataset_label(name: str) -> str:
    """`analytical@0.5` -> `Analytical, rho 0.5`; `airfoil` -> `Airfoil`."""
    if "@" in name:
        base, rho = name.split("@", 1)
        return f"{base.capitalize()}, rho {rho}"
    return dataset_label(name)


def protocol_cell_text(cell: dict, key: str) -> str:
    if not cell.get("valid"):
        return "invalid"
    value = cell.get(key)
    return "n/a" if value is None else f"{fmt_sig(value['mean'])} ± {fmt_sig(value['std'], 2)}"


def render_protocol(protocol: dict) -> str:
    """One table per metric: a row per method, a column per dataset of the registered protocol. A cell the harness could
    not compute reads `invalid` (the reason is listed under the tables); a metric that does not apply to a dataset
    (component error on Airfoil, which has no true components) reads `n/a`."""
    results, datasets = protocol["results"], protocol["datasets"]
    blocks, invalid = [], []
    for key, title, arrow in PROTOCOL_METRICS:
        columns = [d for d in datasets if any(results[m][d].get(key) is not None for m in results)]
        if not columns:
            continue
        header = ["Method"] + [f"{protocol_dataset_label(d)} {arrow}" for d in columns]
        lines = [f"**{title}** ({arrow}: {'lower' if arrow == '↓' else 'higher'} is better)", "",
                 "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]  # fmt: skip
        for m, cells in results.items():
            lines.append("| " + " | ".join([m, *(protocol_cell_text(cells[d], key) for d in columns)]) + " |")
        blocks.append("\n".join(lines))
    for m, cells in results.items():
        for d, cell in cells.items():
            if not cell.get("valid"):
                invalid.append(f"- {m}, {protocol_dataset_label(d)}: {cell.get('invalid_reason')}")
    note = f"Mean ± std over {protocol['n_seeds']} seeds; stability from {protocol['n_boot']} bootstrap refits each."
    tail = ("\n\nInvalid cells:\n" + "\n".join(invalid)) if invalid else ""
    return note + "\n\n" + "\n\n".join(blocks) + tail
