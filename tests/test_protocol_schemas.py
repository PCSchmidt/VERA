"""Schemas 0.10: protocol, figure and retrieval-statistics types (docs/03)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vera.schemas import (
    SCHEMA_VERSION,
    Budget,
    FigureSpec,
    LiteratureSection,
    OutputGuidance,
    ProtocolSpec,
    RetrievalStats,
    RunSpec,
    Topic,
)

SHA = "a" * 64


def protocol(**kw) -> ProtocolSpec:
    base = dict(id="p1", question="q?", methods=["TreeHFD", "TreeSHAP"], datasets=["analytical"],
                metrics=["error", "stability"], primary_metric="error", n_seeds=3,
                target_file="docs/results/target.json", target_sha256=SHA)  # fmt: skip
    return ProtocolSpec(**(base | kw))


def test_the_schema_version_is_at_least_0_10() -> None:  # ProtocolSpec arrived in 0.10
    assert tuple(map(int, SCHEMA_VERSION.split("."))) >= (0, 10)


@pytest.mark.parametrize(
    "bad",
    [{"methods": []}, {"datasets": []}, {"metrics": []}, {"primary_metric": "other"}, {"n_seeds": 0},
     {"target_sha256": "xyz"}, {"target_sha256": "A" * 64}],
)  # fmt: skip
def test_an_invalid_protocol_raises(bad: dict) -> None:
    with pytest.raises(ValidationError):
        protocol(**bad)


def test_a_valid_protocol_round_trips_and_a_run_can_carry_it() -> None:
    p = protocol()
    assert ProtocolSpec.model_validate_json(p.model_dump_json()) == p
    spec = RunSpec(run_id="r", topic=Topic(id="t", text="tt"), protocol=p, guidance=OutputGuidance(max_words=900),
                   budget=Budget(max_usd=1.0, max_wall_seconds=60))  # fmt: skip
    assert spec.protocol.primary_metric == "error"


def test_a_figure_names_its_cells_and_has_a_caption() -> None:
    FigureSpec(id="f1", kind="line", cells=["TreeHFD/analytical/error"], caption="Error against correlation.")
    for bad in ({"cells": []}, {"caption": "  "}, {"kind": "pie"}):
        base = {"id": "f", "kind": "bar", "cells": ["m/d/x"], "caption": "c"} | bad
        with pytest.raises(ValidationError):
            FigureSpec(**base)


def test_retrieval_statistics_ride_on_a_literature_section_and_cannot_be_negative() -> None:
    stats = RetrievalStats(queries=["a", "b"], n_retrieved=100, n_kept=31, n_read_full=6, n_dropped_by_screen=69)
    section = LiteratureSection(run_id="r", topic_id="t", text="x", claims=[], sources=[], retrieval_stats=stats)
    assert LiteratureSection.model_validate_json(section.model_dump_json()).retrieval_stats.n_kept == 31
    assert LiteratureSection(run_id="r", topic_id="t", text="x", claims=[], sources=[]).retrieval_stats is None
    with pytest.raises(ValidationError):
        RetrievalStats(queries=[], n_retrieved=-1, n_kept=0, n_read_full=0, n_dropped_by_screen=0)
