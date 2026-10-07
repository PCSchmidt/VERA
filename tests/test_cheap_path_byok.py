"""Bring-your-own-key: without a Jev (TypeSafe) key the cheap judge path is GLM alone (APP-F-02)."""

from __future__ import annotations

from pathlib import Path

from vera.judge.cheap_path import cheap_path, jev_available
from vera.ledger import Ledger
from vera.schemas import Budget


def names(router) -> list[str]:
    return [b.name for b in router.backends]


def test_without_a_jev_key_every_question_goes_to_glm_alone(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TYPESAFE_AI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    monkeypatch.setattr("vera.backends.ROOT", tmp_path)  # no .env there
    assert not jev_available()
    path = cheap_path(ledger=Ledger.for_run("byok-test", root=tmp_path), budget=Budget(max_usd=1, max_wall_seconds=60))
    assert [b.name for b in path.default.backends] == ["glm-flash"] and [b.name for b in path.loop.backends] == [
        "glm-flash"
    ]


def test_with_a_jev_key_the_default_path_is_jev_then_glm(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TYPESAFE_AI_API_KEY", "ts-test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    assert jev_available()
    path = cheap_path(
        ledger=Ledger.for_run("byok-test-2", root=tmp_path), budget=Budget(max_usd=1, max_wall_seconds=60)
    )
    assert [b.name for b in path.default.backends] == ["jev", "glm-flash"] and [b.name for b in path.loop.backends] == [
        "glm-flash"
    ]
