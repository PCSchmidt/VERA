"""JDG-P-04: the Increment 8 judge set asks the new questions as the pipeline asks them, on the papers' real text."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from vera.literature import sentence_checks

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "judge8" / "items.jsonl"
pytestmark = pytest.mark.skipif(not ITEMS.exists(), reason="the judge set is not built (scripts/build_judge_set8.py)")


def load() -> list[dict]:
    return [json.loads(ln) for ln in ITEMS.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_JDG_P_04_items_are_the_pipelines_own_questions_and_material() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_judge_set8 as b  # noqa: PLC0415

    items = load()
    for pid, folder in b.PAPERS.items():
        doc = json.loads((folder / "paper" / "paper.json").read_text(encoding="utf-8"))
        records = b._jsonl(folder / "retrieved.jsonl") + b._jsonl(folder / "paper" / "added_records.jsonl")
        titles = {r["key"]: r["title"] for r in records}
        claims = {c["id"]: c for c in doc["claims"]}
        for it in (i for i in items if i["paper"] == pid and i["kind"] == "within_quote"):
            c = claims[it["ref"]]
            q, material = sentence_checks.within_quote(c["claim"], c["quote"], titles.get(c["source_key"]))
            assert (it["question"]["id"], it["question"]["text"], it["state"]) == (q.id, q.text, material)
        kept = {i["id"]: i for i in doc["inferences"] if i["status"] == "pass"}
        claim_text = {i: f"{c['claim']} (source: {titles.get(c['source_key'], c['source_key'])})"
                      for i, c in claims.items()}
        for it in (i for i in items if i["paper"] == pid and i["kind"] == "inference" and i["ref"] in kept):
            inf = kept[it["ref"]]
            q, material = sentence_checks.follows_strict(inf["text"], inf["premises"], claim_text)
            assert (it["question"]["text"], it["state"]) == (q.text, material)


def test_JDG_P_04_the_set_is_split_by_paper_with_every_question() -> None:
    items = load()
    split = {i["paper"]: i["split"] for i in items}
    assert split == {"P1": "dev", "N1": "dev", "P2": "test", "P3": "test", "N2": "test"}
    ids = {i["question"]["id"] for i in items}
    assert ids == {"claim.within_quote", "sentence.no_fact", "paper.inference_follows"}
    assert len({i["id"] for i in items}) == len(items)
