# ruff: noqa: E501
"""The landing page's figures come from files, not from the page (APP-F-02, SPEC: no claims the data does not support)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vera.app import facts

ROOT = Path(__file__).resolve().parents[1]


def test_facts_are_built_from_the_committed_files() -> None:
    f = facts.build_facts(ROOT)
    assert {e["id"] for e in f["examples"]} == {"conformal-shift", "research-agents-eval", "tree-explain", "credal-dro"}
    assert f["literature_cost_usd"]["low"] <= f["literature_cost_usd"]["high"]
    assert f["paper_cost_usd"]["low"] <= f["paper_cost_usd"]["high"]
    assert f["review_scores"]["n_reviews"] == 6 and 1 <= f["review_scores"]["weakest_mean"] <= 5
    for e in f["examples"]:
        assert e["topic"] and e["question"] and e["audit"] in {"green", "amber", "red"}
        assert (ROOT / e["document"]).exists() and all((ROOT / p).exists() for p in e["evidence"])


@pytest.mark.parametrize("name", ["literature", "paper"])
def test_the_recorded_spend_equals_the_ledger_when_the_ledger_is_here(name: str) -> None:
    for e in facts.examples(ROOT):
        spec = next(s for s in facts._json(ROOT / "data" / "app" / "examples.json")["examples"] if s["id"] == e["id"])
        ledger = ROOT / spec["ledger"]
        if e["kind"] == name and ledger.exists():  # ledgers other than the named result ones are git-ignored
            assert facts.ledger_total(ROOT, spec["ledger"]) == pytest.approx(e["spent_usd"], abs=5e-5)


def test_the_static_pages_contain_no_figure_of_their_own() -> None:
    """Every number on the landing and examples pages is filled in from /api/facts, so none can drift from the evidence."""
    static = ROOT / "vera" / "app" / "static"
    pages = [p for p in static.glob("*.html")]
    assert pages, "the app has no static pages yet"
    for page in pages:
        text = re.sub(r"<(script|style)\b.*?</\1>", "", page.read_text(encoding="utf-8"), flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        assert not re.search(r"\$\s?\d|\d+\s?%|\b\d+(\.\d+)?\s?(minutes|hours|cents|dollars|papers|runs)\b", text), (
            page.name
        )
