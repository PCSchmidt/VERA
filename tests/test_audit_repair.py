"""Repairing what the final audit failed in a literature section: rewrite to what the quote supports, or drop."""

from __future__ import annotations

import json

from vera.literature import audit_repair
from vera.schemas import Verdict

Q1 = "the decomposition becomes unstable across bootstrap refits when correlation exceeds 0.9"
Q2 = "main effects remain close to the ground truth in the synthetic experiments"
RECORDS = {
    "R1": {
        "key": "R1",
        "title": "TreeHFD",
        "authors": ["C. Benard"],
        "year": "2025",
        "id": "arXiv:2510.24815",
        "url": "https://arxiv.org/abs/2510.24815",
        "source": "arxiv",
    },
    "R2": {
        "key": "R2",
        "title": "Other",
        "authors": [],
        "year": "2019",
        "id": "arXiv:1911.04974",
        "url": "https://arxiv.org/abs/1911.04974",
        "source": "arxiv",
    },
}
PASSAGES = [
    {"source_key": "R1", "id": "R1-P1", "kind": "fulltext", "locator": "sec. 4", "text": f"We find that {Q1}."},
    {"source_key": "R2", "id": "R2-P1", "kind": "fulltext", "locator": "sec. 2", "text": f"We note that {Q2}."},
]
CLAIMS = [
    {
        "claim": "TreeHFD interactions become unstable under strong correlation, unlike TreeSHAP",
        "source_key": "R1",
        "passage_id": "R1-P1",
        "quote": Q1,
    },
    {"claim": "Main effects stay close to the truth", "source_key": "R2", "passage_id": "R2-P1", "quote": Q2},
]
TEXT = (
    "Intro sentence with no citation.\n\n"
    "TreeHFD interactions become unstable under strong correlation, unlike TreeSHAP [R1]. "
    "Main effects stay close to the truth [R2]."
)


def finding(n: int, severity: str = "fail") -> dict:
    return {"check": "claim_support", "severity": severity, "claim_ids": [f"lit:{n}"], "summary": "x"}


def verdict(answer: bool = True, confidence: float = 0.9) -> Verdict:
    return Verdict(question_id="lit.claim_supported", answer=answer, confidence=confidence,
                   confidence_source="self_report", backend="fake", escalated=False, cost_usd=0.0, latency_ms=1,
                   trace_id="t", judge_id="p2.judge")  # fmt: skip


def test_the_failed_sentence_is_mapped_back_to_its_claim() -> None:
    report = {"findings": [finding(0), finding(1, "warn")]}
    assert audit_repair.failed_claims(report, TEXT, CLAIMS) == [0]


def test_a_rewrite_replaces_the_sentence_and_a_removal_leaves_no_gap() -> None:
    new = {"claim": "TreeHFD interactions become unstable under strong correlation", "source_key": "R1",
           "passage_id": "R1-P1", "quote": Q1}  # fmt: skip
    text, claims = audit_repair.apply(TEXT, CLAIMS, 0, new)
    assert "unlike TreeSHAP" not in text and "strong correlation [R1]." in text and claims[0] == new
    text, claims = audit_repair.apply(TEXT, CLAIMS, 1, None)
    assert text.endswith("unlike TreeSHAP [R1].") and len(claims) == 1 and "[R2]" not in text


def run_repair(reply: list, answer: bool = True, confidence: float = 0.9):
    return audit_repair.repair(
        "q?", TEXT, [dict(c) for c in CLAIMS], [0], PASSAGES, RECORDS, lambda prompt: json.dumps(reply),
        lambda q, material: (verdict(answer, confidence), confidence >= 0.7),
    )  # fmt: skip


def test_a_checked_rewrite_is_kept() -> None:
    fix = {"text": "TreeHFD interactions become unstable under strong correlation",
           "claim": {"source_key": "R1", "passage_id": "R1-P1", "quote": Q1}}  # fmt: skip
    text, claims, log = run_repair([fix])
    assert log[0]["outcome"] == "rewritten" and "unlike TreeSHAP" not in text and len(claims) == 2


def test_a_rewrite_with_a_fabricated_quote_or_a_judge_no_is_removed() -> None:
    fake = {"text": "Something new", "claim": {"source_key": "R1", "passage_id": "R1-P1", "quote": "never said"}}
    text, claims, log = run_repair([fake])
    assert log[0]["outcome"] == "removed" and "deterministic" in log[0]["why_removed"] and len(claims) == 1
    fix = {"text": "TreeHFD is unstable", "claim": {"source_key": "R1", "passage_id": "R1-P1", "quote": Q1}}
    _, claims, log = run_repair([fix], answer=False)
    assert log[0]["outcome"] == "removed" and "judge" in log[0]["why_removed"] and len(claims) == 1
    _, claims, log = run_repair([{"text": None, "claim": None}])
    assert log[0]["outcome"] == "removed" and "dropped" in log[0]["why_removed"]


def test_nothing_failed_means_nothing_is_asked() -> None:
    text, claims, log = audit_repair.repair("q?", TEXT, CLAIMS, [], PASSAGES, RECORDS,
                                            lambda p: (_ for _ in ()).throw(AssertionError("asked")), None)  # fmt: skip
    assert (text, claims, log) == (TEXT, CLAIMS, [])


def test_a_rewrite_lists_the_clauses_it_dropped() -> None:
    was = (
        "The LCX set was a moment-type comparator whose size was calibrated by bootstrapping, "
        "so this is not a mean-covariance set tuned under an identical rule"
    )
    now = "The LCX ambiguity set was calibrated by bootstrapping so as to guarantee a desired reliability level"
    dropped = audit_repair.dropped_clauses(was, now)
    assert any("mean-covariance" in c for c in dropped)
    assert audit_repair.dropped_clauses(now, now) == []


def test_a_checked_rewrite_records_what_it_dropped() -> None:
    fix = {"text": "TreeHFD interactions become unstable under strong correlation",
           "claim": {"source_key": "R1", "passage_id": "R1-P1", "quote": Q1}}  # fmt: skip
    _, _, log = run_repair([fix])
    assert log[0]["outcome"] == "rewritten" and any("unlike TreeSHAP" in c for c in log[0]["dropped"])
