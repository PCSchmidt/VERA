"""Degenerate spread: an idea whose results do not vary across seeds while the baseline's do (Increment 5 carry-in).

The Increment 4 credal run reported two ideas whose 100 replications differed by 1e-13 and 1e-5 around means far worse
than the baseline's. A method that responds to the data cannot give the same number on resampled data; spread that
small points at a method that ignores its input, or a fault the run did not diagnose. This is a rule, not a judge: it
compares the relative spread of each metric with the baseline's on the same dataset.
"""

from __future__ import annotations

MIN_VALUES = 10  # fewer replications say nothing about spread
IDEA_REL_SPREAD = 1e-6  # std / |mean| at or below this is "no spread"
BASELINE_REL_SPREAD = 1e-3  # the baseline must visibly vary for the comparison to mean anything


def _rel(cell: object) -> float | None:
    if not isinstance(cell, dict) or "std" not in cell or "mean" not in cell:
        return None
    values = cell.get("values")
    if values is not None and len(values) < MIN_VALUES:
        return None
    scale = abs(cell["mean"])
    return cell["std"] / scale if scale > 1e-12 else None


def degenerate_spread(result: dict, baseline: dict) -> list[str]:
    """Reasons (one per dataset and metric) why `result`'s spread is degenerate against `baseline`; empty if none.

    Both are the harness's per-dataset dicts: dataset -> {metric: {mean, std, values}, ...}."""
    reasons = []
    for dataset, cells in result.items():
        if not isinstance(cells, dict) or not cells.get("valid", True):
            continue
        for metric, cell in cells.items():
            rel, base = _rel(cell), _rel((baseline.get(dataset) or {}).get(metric))
            if rel is not None and base is not None and rel <= IDEA_REL_SPREAD and base >= BASELINE_REL_SPREAD:
                reasons.append(
                    f"{dataset} {metric}: std {cell['std']:.3g} on mean {cell['mean']:.4g} across the seeds "
                    f"(the baseline's relative spread is {base:.2g}); the method does not respond to the data"
                )
    return reasons
