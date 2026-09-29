"""Tests for scripts/fetch_corpus.py path mapping (no network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))  # fetch_corpus imports its sibling discover_corpus
_spec = importlib.util.spec_from_file_location("fetch_corpus", SCRIPTS / "fetch_corpus.py")
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)


def test_local_path_mirrors_site_layout_under_raw() -> None:
    dest = fc.local_path("generated-papers/applications/Time Series_PG-CDIG.pdf")
    assert dest == fc.RAW / "applications" / "Time Series_PG-CDIG.pdf"


@pytest.mark.parametrize("file", ["static/x.pdf", "generated-papers/../../etc/x.pdf"])
def test_local_path_rejects_paths_outside_the_gallery(file: str) -> None:
    with pytest.raises(ValueError):
        fc.local_path(file)
