"""The bridge from a literature run to the research loop: the section's sources become the paper's references."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vera.loop import literature_context as lc

REC = {"title": "TreeHFD", "authors": ["C. Benard"], "year": "2025", "id": "arXiv:2510.24815",
       "url": "https://arxiv.org/abs/2510.24815", "source": "arxiv", "retrieved": "2026-10-02"}  # fmt: skip


def literature_run(tmp_path: Path, text: str, keys=("R5", "R7")) -> Path:
    d = tmp_path / "lit"
    d.mkdir()
    (d / "scope.json").write_text(json.dumps({"run_id": "scope-x-1", "question": "Does X hold?"}), encoding="utf-8")
    (d / "literature.md").write_text(f"## Literature review\n\n{text}\n\n## References\n\n[R5] ...\n", encoding="utf-8")
    records = [{**REC, "key": k, "id": f"arXiv:2510.{i}", "title": f"Paper {k}"} for i, k in enumerate(keys, 1)]
    records.append({**REC, "key": "R9", "title": "Never cited", "id": "arXiv:2510.99"})
    (d / "retrieved.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return d


def fake_fetch(ids: list[str]) -> list[dict]:
    return [{"title": f"Seed {i}", "authors": ["A. B"], "year": "2016", "id": f"arXiv:{i}",
             "url": f"https://arxiv.org/abs/{i}", "source": "arxiv"} for i in ids]  # fmt: skip


def test_the_papers_references_are_the_sections_cited_sources_with_their_keys(tmp_path: Path) -> None:
    lit_dir = literature_run(tmp_path, "One thing [R5]. Another thing [R7]. Again [R5].")
    run_dir = tmp_path / "run"
    lit = lc.prepare(run_dir, lit_dir, fake_fetch)
    records = [json.loads(ln) for ln in (run_dir / "retrieved.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lit["cited"] == ["R5", "R7"] and lit["question"] == "Does X hold?"
    keys = [r["key"] for r in records]
    assert keys[:2] == ["R5", "R7"] and "R9" not in keys  # the never-cited source is not a reference
    assert set(lit["added"].values()) == {"arXiv:2510.24815", "arXiv:1603.02754"}  # seeds, with fresh keys
    assert all(k not in {"R5", "R7", "R9"} for k in lit["added"])
    assert all(r["retrieved"] for r in records)


def test_a_citation_the_literature_run_never_retrieved_is_refused(tmp_path: Path) -> None:
    lit_dir = literature_run(tmp_path, "A claim [R5]. A ghost [R77].")
    with pytest.raises(ValueError, match="R77"):
        lc.prepare(tmp_path / "run", lit_dir, fake_fetch)


def test_a_resumed_run_keeps_its_log_and_fetches_nothing(tmp_path: Path) -> None:
    lit_dir = literature_run(tmp_path, "A claim [R5].")
    lit = lc.prepare(tmp_path / "run", lit_dir, lambda ids: pytest.fail("fetched"), write=False)
    assert lit["cited"] == ["R5"] and not (tmp_path / "run" / "retrieved.jsonl").exists()


def test_the_review_reaches_the_ideas_and_the_write_up_prompts() -> None:
    lit = {"question": "Does X hold?", "text": "Sources agree on Y [R5]."}
    assert "Sources agree on Y [R5]." in lc.for_ideas(lit) and "Does X hold?" in lc.for_ideas(lit)
    prompt = lc.for_write_up(lit)
    assert "Related work" in prompt and "State no number" in prompt and "do not" in prompt
