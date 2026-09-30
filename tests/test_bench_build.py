"""JDG-F-06 benchmark items: labels by construction (risk R3) and the BenchmarkItem schema. No network."""

from __future__ import annotations

import random
import re

import pytest
from pydantic import ValidationError

from vera.bench.build import (
    BASELINE,
    _decimal_shift,
    _digit_change,
    cell_number,
    citation_items,
    eligible_cells,
    fmt_sig,
    loop_items,
    norm_title,
    numeric_items,
    parse_docling_tables,
    perturb,
    swap_word,
)
from vera.schemas import BenchmarkItem, Question, QuestionType

DOCLING = """## Table 1

<!-- caption: Table 1: Error by method. -->
Table 1: Error by method.

| Method | MSE | R2 (%) | Time |
|--------|-----|--------|------|
| Ours   | **0.123** | 91.5 ± 0.2 | 12 |
| Base   | 0.456 | 88.0 | 30 |
| Other  | 0.789 | 85.25% | 7 |

## Table 2

| A | B C D merged |
|---|---|
| x y z | 1 2 3 |
"""


def item(q: Question, label) -> BenchmarkItem:
    return BenchmarkItem(id="t-1", task="loop_gate", split="dev", question=q, state="s", label=label,
                         construction={"kind": "true"}, generator="test")  # fmt: skip


# ── schema ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("q", "label"),
    [
        (Question(id="b", type=QuestionType.BOOLEAN, text="?"), "yes"),
        (Question(id="b", type=QuestionType.BOOLEAN, text="?"), 1),
        (Question(id="c", type=QuestionType.CHOICE, text="?", options=["A", "B"]), "C"),
        (Question(id="s", type=QuestionType.SCORE, text="?", scale=(0, 3)), 4),
        (Question(id="s", type=QuestionType.SCORE, text="?", scale=(0, 3)), True),
    ],
)
def test_JDG_F_06_item_label_must_answer_its_question(q: Question, label) -> None:
    with pytest.raises(ValidationError):
        item(q, label)


def test_JDG_F_06_item_labels_round_trip_with_their_types() -> None:
    for q, label in [
        (Question(id="b", type=QuestionType.BOOLEAN, text="?"), False),
        (Question(id="c", type=QuestionType.CHOICE, text="?", options=["A", "B"]), "B"),
        (Question(id="s", type=QuestionType.SCORE, text="?", scale=(0, 3)), 0),
    ]:
        again = BenchmarkItem.model_validate_json(item(q, label).model_dump_json())
        assert again.label == label and type(again.label) is type(label)


# ── loop_gate ─────────────────────────────────────────────────────────────────


def table_values(state: str) -> tuple[list[str], dict[str, list[float]]]:
    lines = [ln for ln in state.splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = {}
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows[cells[0]] = [float(c.split("±")[0]) for c in cells[1:]]
    return header, rows


def column(header: list[str], dataset: str, metric: str) -> tuple[int, bool]:
    j = next(k for k, h in enumerate(header[1:]) if h.startswith(f"{dataset} · {metric} "))
    return j, header[j + 1].endswith("↓")


def test_JDG_F_06_loop_gate_labels_follow_the_rendered_table() -> None:
    """Re-derive every label from the table text the judge sees, independently of the generator."""
    pairs = loop_items(random.Random(7), n_tables=12, seed=7)
    assert {i.question.type for _, i in pairs} == set(QuestionType)
    for _, it in pairs:
        header, rows = table_values(it.state)
        text = it.question.text
        if it.question.type is QuestionType.BOOLEAN:
            method, metric, dataset = re.match(r'Does "(.+?)" beat .* on (.+?) for the (.+?) dataset', text).groups()
            j, lower = column(header, dataset, metric)
            a, b = rows[method][j], rows[BASELINE][j]
            assert it.label == (a < b if lower else a > b)
        elif it.question.type is QuestionType.CHOICE:
            metric, dataset = re.match(r"Which method has the best mean (.+?) on the (.+?) dataset", text).groups()
            j, lower = column(header, dataset, metric)
            values = {m: v[j] for m, v in rows.items()}
            best = (min if lower else max)(values, key=values.get)
            assert it.label == best and list(values.values()).count(values[best]) == 1
            assert set(it.question.options) == set(rows)
        else:
            cands = re.match(r"How many of the candidate methods \((.+?)\) beat", text).group(1).split(", ")
            metric, dataset = re.search(r"baseline on (.+?) for the (.+?) dataset", text).groups()
            j, lower = column(header, dataset, metric)
            b = rows[BASELINE][j]
            assert it.label == sum((rows[c][j] < b) if lower else (rows[c][j] > b) for c in cands)


def test_JDG_F_06_loop_gate_includes_hard_cases() -> None:
    pairs = loop_items(random.Random(3), n_tables=20, seed=3)
    kinds = {i.construction["kind"] for _, i in pairs}
    assert {"tie", "near_win", "near_loss"} <= kinds
    labels = [i.label for _, i in pairs if i.question.type is QuestionType.BOOLEAN]
    assert 0.3 <= sum(labels) / len(labels) <= 0.7


def test_fmt_sig_keeps_significant_figures() -> None:
    assert fmt_sig(0.0012345, 3) == "0.00123"
    assert fmt_sig(123.456, 4) == "123.5"
    assert fmt_sig(20.0, 3) == "20.0"


# ── numeric ───────────────────────────────────────────────────────────────────


def test_JDG_F_06_docling_tables_parse_and_merged_rows_are_skipped() -> None:
    tables = parse_docling_tables(DOCLING)
    assert len(tables) == 1  # table 2 is not rectangular enough (2 columns)
    t = tables[0]
    assert t.header == ["Method", "MSE", "R2 (%)", "Time"] and t.caption.startswith("Table 1")
    cells = {(t.rows[i][0], t.header[j]): shown for i, j, shown, _ in eligible_cells(t)}
    assert cells[("Ours", "MSE")] == "0.123"  # bold stripped
    assert cells[("Ours", "R2 (%)")] == "91.5"  # ± term ignored
    assert cells[("Other", "R2 (%)")] == "85.25%"


def test_cell_number_rejects_text_and_multiple_numbers() -> None:
    assert cell_number("N/A") is None
    assert cell_number("7,026 / 55.2") is None
    assert cell_number("1,688.3") == ("1,688.3", 1688.3)
    assert cell_number("−0.5") == ("-0.5", -0.5)


@pytest.mark.parametrize("shown", ["0.123", "91.5", "12", "1,688.3", "85.25%", "-0.44"])
def test_JDG_F_06_perturbations_always_change_the_value(shown: str) -> None:
    rng = random.Random(1)
    value = cell_number(shown)[1]
    for _ in range(20):
        for new in (_digit_change(rng, shown), _decimal_shift(rng, shown)):
            if new is not None:
                assert cell_number(new) is not None and cell_number(new)[1] != value


def test_JDG_F_06_numeric_labels_match_the_table() -> None:
    t = parse_docling_tables(DOCLING)[0]
    rng = random.Random(5)
    for cell in eligible_cells(t):
        wrong = perturb(rng, t, cell)
        assert wrong is not None and cell_number(wrong[0])[1] != cell[3]
    pairs = numeric_items(random.Random(2), {"p1": [t], "p2": [t]}, n_bool=10, n_score=2, seed=2)
    for _, it in pairs:
        if it.question.type is QuestionType.BOOLEAN:
            row, col, value = re.search(r'row "(.+?)", column "(.+?)" is (\S+?)\. ', it.question.text).groups()
            i, j = [r[0] for r in t.rows].index(row), t.header.index(col)
            assert it.label == (cell_number(t.rows[i][j])[1] == cell_number(value)[1])


# ── citation ──────────────────────────────────────────────────────────────────


def refs(prefix: str, n: int) -> list[dict]:
    topics = ["graph neural networks", "sparse linear models", "online convex optimization", "deep kernel learning"]
    out = []
    for k in range(1, n + 1):
        title = f"{prefix} study {k} of {topics[k % 4]} for robust inference"
        out.append({"n": k, "title": title, "text": f"A Author. {title}. Venue. 2024"})
    return out


def test_JDG_F_06_citation_labels_true_only_when_the_title_is_listed() -> None:
    by_paper = {"a": refs("Alpha", 30), "b": refs("Beta", 30), "c": refs("Gamma", 30)}
    pairs = citation_items(random.Random(4), by_paper, ["a", "b", "c"], per_paper=8, window=10, seed=4)
    assert len(pairs) == 24
    for paper, it in pairs:
        target = re.search(r'titled "(.+)"\?', it.question.text).group(1)
        listed = {norm_title(ln.split(". ", 1)[1].rsplit(". Venue", 1)[0])
                  for ln in it.state.splitlines() if ln.startswith("[")}  # fmt: skip
        assert it.label == (norm_title(target) in listed), (it.construction, target)
        assert it.construction["source"] == paper


def test_swap_word_changes_meaning_word_and_keeps_case() -> None:
    assert swap_word(random.Random(0), "Sparse models for Online learning") in {
        "Dense models for Online learning",
        "Sparse models for Offline learning",
    }
    assert swap_word(random.Random(0), "Nothing to swap here") is None
