"""JDG-F-06: benchmark metrics and the offline threshold sweep, on fixed fake verdicts. No network."""

from __future__ import annotations

import pytest

from vera.bench.metrics import Rec, backend_metrics, ece, modal_answers, percentile, same, sweep


def rec(item: str, answer, label=True, *, repeat=0, conf=0.9, backend="cheap", cost=0.001, lat=100, task="t",
        source="self_report") -> Rec:  # fmt: skip
    return Rec(backend, item, repeat, task, label, answer, conf, source, cost, lat)


def test_JDG_F_06_agreement_flip_and_malformed_rates() -> None:
    recs = [
        rec("a", True, repeat=0), rec("a", True, repeat=1),  # stable, right
        rec("b", True, False, repeat=0), rec("b", False, False, repeat=1),  # flips: 1 right of 2
        rec("c", "", 2, repeat=0, conf=0.0, source="none"), rec("c", 2, 2, repeat=1),  # one malformed
    ]  # fmt: skip
    m = backend_metrics(recs, reference_modes={"a": True, "b": False, "c": 2})
    assert m["agreement_label"] == pytest.approx(4 / 6)
    assert m["agreement_reference"] == pytest.approx(4 / 6)
    assert m["flip_rate"] == pytest.approx(2 / 3)  # items b and c are not stable
    assert m["flip_rate_verdicts"] == pytest.approx(2 / 6)
    assert m["malformed_rate"] == pytest.approx(1 / 6)
    assert (m["items"], m["repeats"], m["verdicts"]) == (3, 2, 6)
    assert m["confidence_sources"] == {"self_report": 5, "none": 1}


def test_JDG_F_06_true_is_not_one() -> None:
    assert not same(True, 1) and same(1, 1) and same("B", "B")
    m = backend_metrics([rec("a", 1, True)], reference_modes={"a": True})
    assert m["agreement_label"] == 0.0 and m["agreement_reference"] == 0.0


def test_JDG_F_06_ece_zero_when_calibrated_and_large_when_overconfident() -> None:
    calibrated = [rec(str(i), True, conf=0.75) for i in range(3)] + [rec("x", False, conf=0.75)]
    assert ece(calibrated) == pytest.approx(0.0)
    overconfident = [rec(str(i), i < 5, conf=1.0) for i in range(10)]  # 50% right at confidence 1.0
    assert ece(overconfident) == pytest.approx(0.5)


def test_JDG_F_06_modal_answer_and_percentiles() -> None:
    assert modal_answers([rec("a", False), rec("a", True), rec("a", True)]) == {"a": True}
    assert modal_answers([rec("a", "B"), rec("a", "C")]) == {"a": "B"}  # tie: first seen
    assert percentile([100, 200, 300, 400], 50) == 200 and percentile([100, 200, 300, 400], 95) == 400
    assert percentile([], 50) == 0.0


def test_JDG_F_06_sweep_escalates_below_threshold_and_adds_costs() -> None:
    cheap = [
        rec("a", True, conf=0.9, cost=0.001, lat=100),  # confident and right
        rec("b", True, False, conf=0.4, cost=0.001, lat=100),  # unsure and wrong
    ]
    ref = [
        rec("a", True, backend="ref", cost=0.01, lat=1000),
        rec("b", False, False, backend="ref", cost=0.01, lat=1000),
    ]
    rows = {r["threshold"]: r for r in sweep(cheap, ref, thresholds=[0.0, 0.5, 1.0])}
    assert rows[0.0]["escalation_rate"] == 0 and rows[0.0]["agreement_label"] == 0.5
    assert rows[0.0]["cost_per_item_usd"] == pytest.approx(0.001)
    assert rows[0.5]["escalation_rate"] == 0.5 and rows[0.5]["agreement_label"] == 1.0
    assert rows[0.5]["cost_per_item_usd"] == pytest.approx((0.001 + 0.011) / 2)
    assert rows[0.5]["cost_ratio_to_reference"] == pytest.approx(0.6)
    assert rows[1.0]["escalation_rate"] == 1.0 and rows[1.0]["agreement_reference"] == 1.0
    assert rows[1.0]["latency_p50_ms"] == 1100


def test_JDG_F_06_sweep_pairs_cheap_repeats_with_reference_repeats() -> None:
    cheap = [rec("a", True, repeat=r, conf=0.0) for r in range(4)]
    ref = [rec("a", True, backend="ref", repeat=0), rec("a", False, backend="ref", repeat=1)]
    (row,) = sweep(cheap, ref, thresholds=[0.5])
    assert row["agreement_label"] == 0.5  # repeats 0, 2 -> ref repeat 0 (right); 1, 3 -> ref repeat 1 (wrong)
