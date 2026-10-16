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
            # a paper made later from the review adds to the same ledger; the review's spend is what it held before
            made = ROOT / "runs" / ledger.stem.removeprefix("run_") / "paper" / "app_paper_request.json"
            total = facts._json(made)["spent_before_usd"] if made.exists() else facts.ledger_total(ROOT, spec["ledger"])
            assert total == pytest.approx(e["spent_usd"], abs=5e-5)


def test_the_review_paper_cost_comes_from_the_showcase_papers() -> None:
    specs = facts._json(ROOT / "data" / "app" / "showcase.json")["examples"]
    spent = [s["paper"]["spent_usd"] for s in specs if s.get("paper")]
    assert facts.build_facts(ROOT)["review_paper_cost_usd"] == {"low": min(spent), "high": max(spent)}


def test_the_models_shown_are_the_ones_the_code_uses() -> None:
    from vera.app.pipeline import DEFAULT_MODEL
    from vera.bench.candidates import OPENROUTER

    m = facts.build_facts(ROOT)["models"]
    assert m == {"writer": DEFAULT_MODEL[1], "cheap_judge": OPENROUTER["glm-flash"][0], "reference": OPENROUTER["sonnet-ref"][0]}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert all(f"`{slug}`" in readme for slug in m.values())  # the README's table names the same models


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
