"""Tests for scripts/map_parents.py and scripts/resolve_parents.py: parsing and matching, no network."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mp = _load("map_parents")
rp = _load("resolve_parents")

# Shape of the arXiv HTML appendix after html_to_text, including the table-of-contents
# "A.2" line that appears before the tables.
APPENDIX = """
 A.2 Configuration
 Table 12: NeurIPS 2025 Papers. We utilize 2 accepted papers.
 Title
 SAVVY: Spatial Awareness via Audio-Visual LLMs through Seeing and Hearing ( Chen et al., 2025b )
 Least squares variational inference ( Fay et al., 2025 )
 Table 14: ICML 2026 Spotlight Papers. We utilize 1 papers accepted as spotlight presentations.
 Title
 Incremental BPE Tokenization ( Jiang and Gong, 2026 )
 A.2 Configuration
 Unless otherwise specified ( see below, 2026 )
"""


def test_parse_candidates_reads_tables_and_venues() -> None:
    rows = mp.parse_candidates(APPENDIX)
    assert [(r["parent_title"], r["parent_venue"], r["cite"]) for r in rows] == [
        (
            "SAVVY: Spatial Awareness via Audio-Visual LLMs through Seeing and Hearing",
            "NeurIPS 2025",
            "Chen et al., 2025b",
        ),
        ("Least squares variational inference", "NeurIPS 2025", "Fay et al., 2025"),
        ("Incremental BPE Tokenization", "ICML 2026 (spotlight)", "Jiang and Gong, 2026"),
    ]


def test_squash_undoes_line_breaks_and_hyphenation() -> None:
    assert mp.squash("Incremental BPE Tok-\nenization") == mp.squash("Incremental BPE Tokenization")


def test_suggest_prefers_exact_title_then_method_name() -> None:
    cands = mp.parse_candidates(APPENDIX)
    text = "We improve on Incremental BPE\nTokenization (Jiang & Gong). Least squares and variational ideas."
    ranked = mp.suggest(text, "VD-STrans", cands)
    assert ranked[0]["parent_title"] == "Incremental BPE Tokenization"
    assert ranked[0]["how"] == "exact title"
    ranked = mp.suggest("spatial audio", "SAVVY-Vortex", cands)
    assert ranked[0]["parent_title"].startswith("SAVVY") and ranked[0]["tier"] == 1


FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2506.05414v2</id>
    <title>SAVVY: Spatial Awareness via Audio-Visual LLMs through
      Seeing and Hearing</title></entry>
  <entry><id>http://arxiv.org/abs/2401.00001v1</id><title>Something else entirely</title></entry>
</feed>"""


def test_parse_feed_strips_version_and_whitespace() -> None:
    assert rp.parse_feed(FEED)[0] == (
        "2506.05414",
        "SAVVY: Spatial Awareness via Audio-Visual LLMs through Seeing and Hearing",
    )


def test_best_match_requires_a_close_title() -> None:
    entries = rp.parse_feed(FEED)
    hit = rp.best_match("SAVVY: Spatial Awareness via Audio-Visual LLMs through Seeing and Hearing", entries)
    assert hit is not None and hit[0] == "2506.05414"
    assert rp.best_match("Spatial Hearing in Robots", entries) is None


def test_query_for_drops_stopwords_and_punctuation() -> None:
    assert rp.query_for("Hogwild! Inference: Parallel LLM Generation") == (
        "ti:Hogwild AND ti:Inference AND ti:Parallel AND ti:LLM AND ti:Generation"
    )


def test_parse_openreview_reads_forum_title_venue_pdf() -> None:
    payload = (
        '{"notes": [{"id": "aUXiqhLh0S", "forum": "aUXiqhLh0S", "content": {'
        '"title": {"value": "Balanced Active Inference"}, "venue": {"value": "NeurIPS 2025 poster"}, '
        '"pdf": {"value": "/pdf/cd6a.pdf"}}}]}'
    )
    assert rp.parse_openreview(payload) == [
        {
            "forum": "aUXiqhLh0S",
            "title": "Balanced Active Inference",
            "venue": "NeurIPS 2025 poster",
            "pdf": "/pdf/cd6a.pdf",
        }
    ]
