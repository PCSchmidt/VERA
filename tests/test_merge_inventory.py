"""Tests for scripts/merge_inventory_rows.py validation (no network)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_inventory_rows.py"
_spec = importlib.util.spec_from_file_location("merge_inventory_rows", SCRIPT)
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)

CANDS = {
    "Parent A": {"parent_title": "Parent A", "parent_venue": "NeurIPS 2025", "paper_id": "2501.00001"},
    "Parent B": {"parent_title": "Parent B", "parent_venue": "ICLR 2026", "paper_id": "unknown"},
}
INVENTORY = [{"gen_paper_id": "d/p1", "parent_title": ""}, {"gen_paper_id": "d/p2", "parent_title": ""}]


def row(pid: str, parent: str = "Parent A", **over: str) -> dict[str, str]:
    base = {
        "gen_paper_id": pid, "gen_code_url": "none", "parent_title": parent,
        "parent_venue": CANDS[parent]["parent_venue"], "parent_id_arxiv_or_doi": CANDS[parent]["paper_id"],
        "parent_code_url": "unknown", "reported_gain_pct": "unknown", "compute_class": "cpu",
        "candidate_for_p3": "no", "notes": "Parent: x. Gain: y. Compute: z.",
    }  # fmt: skip
    return base | over


def test_valid_rows_pass() -> None:
    assert mi.validate([row("d/p1"), row("d/p2", "Parent B")], INVENTORY, CANDS) == []


def test_shared_parent_is_rejected() -> None:
    problems = mi.validate([row("d/p1"), row("d/p2")], INVENTORY, CANDS)
    assert any("parent shared" in p for p in problems)


def test_unknown_candidate_venue_and_id_mismatch_are_rejected() -> None:
    problems = mi.validate(
        [row("d/p1", parent_title="Not a candidate"), row("d/p2", "Parent B", parent_venue="ICML 2026")],
        INVENTORY,
        CANDS,
    )
    assert any("not one of the 107" in p for p in problems)
    assert any("parent_venue" in p for p in problems)


def test_bad_values_are_rejected() -> None:
    problems = mi.validate(
        [row("d/p1", compute_class="gpu", reported_gain_pct="~5%", gen_code_url="github"), row("d/x", "Parent B")],
        INVENTORY,
        CANDS,
    )
    assert any("compute_class" in p for p in problems)
    assert any("reported_gain_pct" in p for p in problems)
    assert any("code URL" in p for p in problems)
    assert any("d/x: not a listed paper" in p for p in problems)
