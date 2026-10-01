"""Benchmark metrics and the offline threshold sweep (JDG-F-06). Pure functions over recorded verdicts.

A `Rec` is one recorded verdict: one backend's answer to one test item on one
repeat. Metrics per backend:

- agreement_label: share of verdicts whose answer equals the item's label;
- agreement_reference: share equal to the reference judge's modal answer for
  the item (its most common answer across repeats; ties broken by first seen);
- ece: expected calibration error of `confidence` against correctness (vs the
  label), 10 equal-width bins;
- flip_rate: share of items whose answers are not all the same across
  repeats (JDG-P-03); flip_rate_verdicts: share of verdicts that differ from
  their item's modal answer;
- malformed_rate: share of verdicts with confidence source "none";
- cost_per_item_usd (mean per verdict), latency p50 / p95 (ms).

The sweep replays the router (`vera.judge.router`, one escalation) offline:
at threshold t a cheap verdict stands if its confidence >= t, else the
reference's verdict for the same item replaces it (repeat r of the cheap
backend pairs with repeat r mod R of the reference). Cost and latency of an
escalated item are the cheap call's plus the reference call's, as they would
be live. No model is called.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

THRESHOLDS = [round(0.05 * k, 2) for k in range(21)]  # 0.00, 0.05, ..., 1.00


@dataclass(frozen=True)
class Rec:
    backend: str
    item: str
    repeat: int
    task: str
    label: bool | int | str
    answer: bool | int | str
    confidence: float
    source: str
    cost_usd: float
    latency_ms: int


def same(a: bool | int | str, b: bool | int | str) -> bool:
    """Answer equality that keeps True distinct from 1."""
    return type(a) is type(b) and a == b


def _key(answer: bool | int | str) -> tuple[str, str]:
    return (type(answer).__name__, str(answer))


def modal_answers(recs: Iterable[Rec]) -> dict[str, bool | int | str]:
    """Each item's most common answer (first seen wins a tie)."""
    by_item: dict[str, list[bool | int | str]] = defaultdict(list)
    for r in recs:
        by_item[r.item].append(r.answer)
    out = {}
    for item, answers in by_item.items():
        counts = Counter(_key(a) for a in answers)
        top = max(counts.values())
        out[item] = next(a for a in answers if counts[_key(a)] == top)
    return out


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..100); 0.0 for no values."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, -(-len(s) * q // 100) - 1))
    return float(s[int(k)])


def ece(recs: list[Rec], bins: int = 10) -> float:
    """Expected calibration error of confidence against correctness (vs the label)."""
    if not recs:
        return 0.0
    buckets: dict[int, list[Rec]] = defaultdict(list)
    for r in recs:
        buckets[min(int(r.confidence * bins), bins - 1)].append(r)
    total = 0.0
    for members in buckets.values():
        acc = sum(same(r.answer, r.label) for r in members) / len(members)
        conf = sum(r.confidence for r in members) / len(members)
        total += len(members) / len(recs) * abs(acc - conf)
    return total


def backend_metrics(recs: list[Rec], reference_modes: dict[str, bool | int | str]) -> dict:
    if not recs:
        raise ValueError("no verdicts for this backend")
    modes = modal_answers(recs)
    by_item: dict[str, list[Rec]] = defaultdict(list)
    for r in recs:
        by_item[r.item].append(r)
    flips = [len({_key(r.answer) for r in rs}) > 1 for rs in by_item.values()]
    by_task: dict[str, list[Rec]] = defaultdict(list)
    for r in recs:
        by_task[r.task].append(r)
    latencies = [float(r.latency_ms) for r in recs]
    return {
        "verdicts": len(recs),
        "items": len(by_item),
        "repeats": max(r.repeat for r in recs) + 1,
        "agreement_label": sum(same(r.answer, r.label) for r in recs) / len(recs),
        "agreement_reference": _agreement_ref(recs, reference_modes),
        "ece": ece(recs),
        "flip_rate": sum(flips) / len(flips),
        "flip_rate_verdicts": sum(not same(r.answer, modes[r.item]) for r in recs) / len(recs),
        "malformed_rate": sum(r.source == "none" for r in recs) / len(recs),
        "confidence_sources": dict(Counter(r.source for r in recs)),
        "cost_per_item_usd": sum(r.cost_usd for r in recs) / len(recs),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "agreement_label_by_task": {
            t: sum(same(r.answer, r.label) for r in rs) / len(rs) for t, rs in sorted(by_task.items())
        },
    }


def _agreement_ref(recs: list[Rec], reference_modes: dict[str, bool | int | str]) -> float | None:
    scored = [r for r in recs if r.item in reference_modes]
    if not scored:
        return None
    return sum(same(r.answer, reference_modes[r.item]) for r in scored) / len(scored)


def sweep(cheap: list[Rec], reference: list[Rec], thresholds: list[float] = THRESHOLDS) -> list[dict]:
    """The router replayed offline at each threshold: cheap first, escalate below t to the reference."""
    ref_by: dict[str, list[Rec]] = defaultdict(list)
    for r in sorted(reference, key=lambda r: r.repeat):
        ref_by[r.item].append(r)
    ref_modes = modal_answers(reference)
    ref_cost = statistics.fmean(r.cost_usd for r in reference)
    rows = []
    for t in thresholds:
        final, costs, lats, escalated = [], [], [], 0
        for c in cheap:
            refs = ref_by.get(c.item)
            if c.confidence >= t or not refs:
                final.append(c)
                costs.append(c.cost_usd)
                lats.append(float(c.latency_ms))
                continue
            r = refs[c.repeat % len(refs)]
            escalated += 1
            final.append(r)
            costs.append(c.cost_usd + r.cost_usd)
            lats.append(float(c.latency_ms + r.latency_ms))
        cost = sum(costs) / len(costs)
        rows.append({
            "threshold": t,
            "agreement_label": sum(same(r.answer, r.label) for r in final) / len(final),
            "agreement_reference": sum(same(r.answer, ref_modes[r.item]) for r in final if r.item in ref_modes)
            / max(1, sum(r.item in ref_modes for r in final)),
            "escalation_rate": escalated / len(cheap),
            "cost_per_item_usd": cost,
            "cost_ratio_to_reference": cost / ref_cost if ref_cost else None,
            "latency_p50_ms": percentile(lats, 50),
            "latency_p95_ms": percentile(lats, 95),
        })  # fmt: skip
    return rows
