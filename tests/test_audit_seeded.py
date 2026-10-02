"""AUD-F-03, AUD-F-04 on the seeded-fault set (data/seeded/), offline: the audit's deterministic layer and a correct
judge, with no bibliographic sources. The live run (real judge, real Crossref and arXiv) is recorded in
data/seeded/results_{dev,test}.json and checked by tools/checks/check_seeded.py (gate `audit_ready`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_audit import CorrectJudge
from vera.audit.seeded import (
    FAULT_TYPES,
    compute_test_hash,
    evaluate,
    load_manifest,
    perturb_digit,
    plant,
    verify_split,
)

ROOT = Path(__file__).resolve().parents[1]
TARGET = json.loads((ROOT / "docs" / "results" / "treehfd_baseline_target.json").read_text(encoding="utf-8"))
HAVE_SET = (ROOT / "data" / "seeded" / "split.json").exists()
needs_set = pytest.mark.skipif(not HAVE_SET, reason="data/seeded is not built (scripts/build_seeded_faults.py)")


def stub_lookup(title: str) -> list[dict]:
    return []  # offline: no bibliographic source knows a fabricated title


@needs_set
def test_AUD_F_03_the_set_is_split_by_base_paper_with_every_fault_type_in_both_halves() -> None:
    rows = load_manifest(ROOT)
    split = json.loads((ROOT / "data" / "seeded" / "split.json").read_text(encoding="utf-8"))
    assert not set(split["dev_bases"]) & set(split["test_bases"])
    for half in ("dev", "test"):
        types = [r["fault_type"] for r in rows if r["split"] == half]
        assert types.count("control") >= 3
        assert all(types.count(t) >= 3 for t in FAULT_TYPES)  # three planted faults of each type per half
    assert {r["split"] for r in rows if r["paper_id"] in split["test_bases"]} == {"test"}


@needs_set
def test_AUD_F_03_the_test_split_is_unchanged_since_its_hash_was_recorded() -> None:
    assert verify_split(ROOT)["test_sha256"] == compute_test_hash(ROOT)


@needs_set
@pytest.mark.parametrize("split", ["dev", "test"])
def test_AUD_F_03_AUD_F_04_planted_faults_are_detected_and_controls_stay_clean(split: str) -> None:
    rows, summary = evaluate(ROOT, split, ask=CorrectJudge(), lookup=stub_lookup, target=TARGET)
    assert summary["controls"] >= 3 and summary["false_fails"] == 0, [r for r in rows if r["fault_type"] == "control"]
    assert summary["detection_rate"] >= 0.9, [r["fault_id"] for r in rows if not r["detected"]]
    for kind, counts in summary["by_type"].items():  # and no fault type goes unflagged (amber or red)
        assert counts["flagged"] >= 0.9 * counts["n"], (kind, counts)


@needs_set
def test_AUD_F_03_a_changed_test_item_is_refused_not_evaluated(tmp_path: Path) -> None:
    import shutil  # noqa: PLC0415

    shutil.copytree(ROOT / "data" / "seeded", tmp_path / "data" / "seeded")
    victim = next(
        p for p in (tmp_path / "data" / "seeded" / "papers").iterdir() if p.name.startswith("run-smoke-006__numeric")
    )
    victim.write_text(victim.read_text(encoding="utf-8") + "\nTampered.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="test items changed"):
        evaluate(tmp_path, "test", ask=CorrectJudge(), lookup=stub_lookup, target=TARGET)


# ── planting ─────────────────────────────────────────────────────────────────────────────────────────


@needs_set
@pytest.mark.parametrize("kind", FAULT_TYPES)
def test_AUD_F_03_planting_is_deterministic_and_changes_the_paper(kind: str) -> None:
    import random  # noqa: PLC0415

    base = ROOT / "data" / "seeded" / "base" / "run-smoke-006"
    text = (base / "paper.md").read_text(encoding="utf-8")
    results = json.loads((base / "results.json").read_text(encoding="utf-8"))
    a = plant(kind, text, results, random.Random(1))
    b = plant(kind, text, results, random.Random(1))
    assert a is not None and a == b and a[0] != text


def test_AUD_F_03_perturb_digit_changes_exactly_one_digit_and_keeps_a_positive_number() -> None:
    import random  # noqa: PLC0415

    rng = random.Random(0)
    for x in ("2.79", "0.57", "31.35", "5"):
        y = perturb_digit(x, rng)
        assert y != x and len(y) == len(x) and sum(a != b for a, b in zip(x, y, strict=True)) == 1 and float(y) > 0
