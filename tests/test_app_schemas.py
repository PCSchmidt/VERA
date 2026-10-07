"""App contracts (docs/03 0.11)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vera.schemas import AppConfig, RunRequest, RunStatus

GOOD = {"run_id": "my-first-run", "topic": "How do tree ensembles behave under correlated features?",
        "max_usd": 1.0, "max_wall_seconds": 3600}  # fmt: skip


def test_a_good_request_loads_with_defaults() -> None:
    r = RunRequest(**GOOD)
    assert r.allow_experiments is False and r.guidance.format == "paper"


@pytest.mark.parametrize("change", [
    {"run_id": "A"}, {"run_id": "../escape"}, {"run_id": "ab"}, {"run_id": "x" * 65}, {"run_id": "has space"},
    {"topic": "   "}, {"topic": "t" * 2001}, {"max_usd": 0}, {"max_usd": -1}, {"max_usd": 25.01},
    {"max_wall_seconds": 0}, {"api_key": "sk-anything"},
])  # fmt: skip
def test_a_malformed_request_raises(change: dict) -> None:
    with pytest.raises(ValidationError):
        RunRequest(**{**GOOD, **change})


def test_the_status_and_config_cannot_carry_a_key() -> None:
    with pytest.raises(ValidationError):
        AppConfig(docker_available=True, grobid_available=False, key_source="session", openalex_key=False,
                  semantic_scholar_key=False, api_key="sk-x")  # fmt: skip
    with pytest.raises(ValidationError):
        RunStatus(run_id="abc", state="running", max_usd=1.0, key="sk-x")
    assert not [f for f in AppConfig.model_fields if "key" in f and f != "key_source" and not f.endswith("_key")]
    with pytest.raises(ValidationError):
        RunStatus(run_id="abc", state="unknown-state", max_usd=1.0)
