"""What the first-run checklist shows: is a key available, is Docker there, is GROBID up (never the key itself)."""

from __future__ import annotations

import os
from collections.abc import Callable

import httpx

from vera.app.keystore import SessionKey
from vera.backends import api_key
from vera.sandbox.host import docker_available
from vera.schemas import AppConfig

GROBID_URL = "http://localhost:8070/api/isalive"


def _has(name: str) -> bool:
    try:
        api_key(name)
    except KeyError:
        return False
    return True


def grobid_probe() -> bool:
    try:
        return httpx.get(GROBID_URL, timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


def detect(
    session: SessionKey, *, docker: Callable[[], bool] = docker_available, grobid: Callable[[], bool] = grobid_probe
) -> AppConfig:
    if session.present:
        source = "session"
    elif os.environ.get("OPENROUTER_API_KEY") or _has("OPENROUTER_API_KEY"):
        source = "env"
    else:
        source = "none"
    return AppConfig(
        docker_available=docker(), grobid_available=grobid(), key_source=source,
        openalex_key=_has("OPENALEX_API_KEY"), semantic_scholar_key=_has("SEMANTIC_SCHOLAR_API_KEY"),
    )  # fmt: skip
