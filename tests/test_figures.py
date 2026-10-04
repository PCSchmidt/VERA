# ruff: noqa: E501
"""Figures drawn by VERA from results.json, and the audit of their data against their source cells."""

from __future__ import annotations

import json
from pathlib import Path

from vera.audit.figure_check import audit_figures
from vera.loop import figures, tables
from vera.loop.writeup import check_guidance, place_figures
from vera.schemas import OutputGuidance


def cell(mean: float) -> dict:
    return {"valid": True, "invalid_reason": None, "n_seeds": 3, "n_boot": 5, "component_mse_pct": {"mean": mean, "std": 0.2},
            "rank_stability": {"mean": 0.9, "std": 0.01}}  # fmt: skip


def results_json() -> dict:
    datasets = ["analytical@0", "analytical@0.5", "analytical@0.95"]
    metric = {"mean": 2.0, "std": 0.1, "values": [2.0]}
    results = {tables.BASELINE: {"analytical": {"valid": True, tables.PRIMARY: metric}}}
    protocol = {"datasets": datasets, "methods": ["TreeHFD", "TreeSHAP"], "n_seeds": 3, "n_boot": 5,
                "results": {m: {d: cell(5.0 + i + 0.1 * j) for j, d in enumerate(datasets)} for i, m in enumerate(["TreeHFD", "TreeSHAP"])}}  # fmt: skip
    return {"results": results, "datasets": ["analytical"], "protocol": protocol, "n_seeds": 3}


def test_the_plan_draws_the_protocol_and_results_figures_and_their_data_equal_their_cells(tmp_path: Path) -> None:
    rj = results_json()
    planned = figures.plan(rj)
    assert [p["spec"].id for p in planned] == ["fig_component_mse_pct", "fig_rank_stability", f"fig_{tables.PRIMARY}"]
    records = figures.draw(rj, planned, tmp_path)
    assert all((tmp_path / r["file"]).stat().st_size > 1000 for r in records)
    assert figures.check_data(rj, records) == []
    assert json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))[0]["id"] == "fig_component_mse_pct"


def test_a_figure_drawn_from_altered_numbers_is_a_fail(tmp_path: Path) -> None:
    rj = results_json()
    records = figures.draw(rj, figures.plan(rj), tmp_path)
    first = next(iter(records[0]["data"].values()))[0]
    first["mean"] += 1.0  # the plotted point no longer equals its cell
    _, findings = audit_figures("![Figure 1](figures/fig_component_mse_pct.png)", rj, records)
    assert [f.severity for f in findings] == ["fail"] and "was plotted as" in findings[0].summary


def test_an_image_vera_did_not_draw_is_a_fail(tmp_path: Path) -> None:
    rj = results_json()
    records = figures.draw(rj, figures.plan(rj), tmp_path)
    _, findings = audit_figures("![x](figures/made_up.png)", rj, records)
    assert any("did not draw" in f.summary for f in findings)


def test_the_guidance_check_wants_each_figure_in_the_report_and_referred_to(tmp_path: Path) -> None:
    rj = results_json()
    records = figures.draw(rj, figures.plan(rj), tmp_path)[:1]
    g = OutputGuidance(format="paper", required_sections=[])
    bare = "## Results\n\nSome text."
    assert len(check_guidance(bare, g, [], records)) == 2  # missing, and not referred to
    placed = place_figures("## Results\n\nSome text.", records)
    assert check_guidance(placed, g, [], records) == []  # VERA appends the image, a caption and a sentence that refers to it
    kept = place_figures("## Results\n\nFigure 1 shows it.\n\n[[FIGURE:fig_component_mse_pct]]\nFigure 1. A caption.", records)
    assert "figures/fig_component_mse_pct.png" in kept and check_guidance(kept, g, [], records) == []
