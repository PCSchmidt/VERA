"""Tests for scripts/discover_corpus.py: parsing and seeding only, no network."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discover_corpus.py"
_spec = importlib.util.spec_from_file_location("discover_corpus", SCRIPT)
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

# Trimmed from the live page's structure (2026-09-29), including its awkward cases:
# a space in a file name, and a file name misspelt relative to its label.
PAGE = """
<meta name="description" content="beats human state-of-the-art on 86 of 107 research problems">
<strong id="total-count">3</strong> papers autonomously generated
<script type="module">
    const categories = [
        { key: 'applications',   name: 'Applications' },
        { key: 'social_aspects', name: 'Social Aspects' },
    ];
    const paperData = {
        applications: [
            { label: "Health (Cartan-DEC-MiAE)", file: "generated-papers/applications/Health_Cartan-DEC-MiAE.pdf" },
            { label: "Time Series (PG-CDIG)", file: "generated-papers/applications/Time Series_PG-CDIG.pdf" },
        ],
        social_aspects: [
            { label: "Robustness (IMD-GV)", file: "generated-papers/social_aspects/Robusntess_IMD-GV.pdf" },
        ],
    };
    const MAX_PAGE_WIDTH = 900;
</script>
"""


def test_parse_listing_domains_subdomains_methods() -> None:
    papers = dc.parse_listing(PAGE)
    assert [(p["domain"], p["subdomain"], p["method_name"]) for p in papers] == [
        ("Applications", "Health", "Cartan-DEC-MiAE"),
        ("Applications", "Time Series", "PG-CDIG"),
        ("Social Aspects", "Robustness", "IMD-GV"),
    ]
    # the id comes from the file, so it stays stable even where the label differs
    assert papers[2]["gen_paper_id"] == "social_aspects/Robusntess_IMD-GV"


def test_pdf_url_encodes_spaces_per_segment() -> None:
    papers = dc.parse_listing(PAGE)
    assert papers[1]["pdf_url"] == (
        "https://scientist-two.github.io/generated-papers/applications/Time%20Series_PG-CDIG.pdf"
    )


def test_split_label_uses_last_parenthesis() -> None:
    assert dc.split_label("Causality (SPECTRA-HET SPLIT UP)") == ("Causality", "SPECTRA-HET SPLIT UP")
    assert dc.split_label("No method") == ("No method", "")


def test_stated_count_and_explanation() -> None:
    papers = dc.parse_listing(PAGE)
    stated = dc.parse_stated_count(PAGE)
    assert stated == 3
    text = dc.explain(PAGE, stated, papers, [p["file"] for p in papers])
    assert "matches its listing" in text
    assert "86 of 107" in text
    assert "exactly these 3 PDFs" in text


def test_explanation_reports_repo_mismatch() -> None:
    papers = dc.parse_listing(PAGE)
    repo = [p["file"] for p in papers[:2]] + ["generated-papers/rl/Extra.pdf"]
    text = dc.explain(PAGE, 4, papers, repo)
    assert "states 4 papers but its listing has 3" in text
    assert "Extra.pdf" in text and "Robusntess_IMD-GV.pdf" in text


def test_seed_inventory_drops_template_and_keeps_filled_rows() -> None:
    papers = dc.parse_listing(PAGE)
    template = dict.fromkeys(dc.INVENTORY_COLUMNS, "") | {"gen_paper_id": dc.TEMPLATE_ID}
    filled = dict.fromkeys(dc.INVENTORY_COLUMNS, "x") | {"gen_paper_id": papers[0]["gen_paper_id"]}
    gone = dict.fromkeys(dc.INVENTORY_COLUMNS, "") | {"gen_paper_id": "rl/Removed"}
    rows, stale = dc.seed_inventory([template, filled, gone], papers)
    ids = [r["gen_paper_id"] for r in rows]
    assert dc.TEMPLATE_ID not in ids
    assert rows[0] == filled  # filled row untouched
    assert set(ids) == {p["gen_paper_id"] for p in papers} | {"rl/Removed"}
    assert stale == ["rl/Removed"]
    new = next(r for r in rows if r["gen_paper_id"] == papers[1]["gen_paper_id"])
    assert (new["domain"], new["subdomain"], new["method_name"]) == ("Applications", "Time Series", "PG-CDIG")
    assert new["gen_pdf_url"] == ""  # filled by fetch_corpus.py once the download succeeds
