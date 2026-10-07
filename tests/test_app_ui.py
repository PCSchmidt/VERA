# ruff: noqa: E501
"""The pages render without error against fixture runs (SPEC ui_ready): a finished run, a stopped run, a run stopped at its
budget, a run with a red audit, and the examples. Uses a headless Chrome or Edge when one is installed, else is skipped."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
import uvicorn  # noqa: E402

from vera.app import state as app_state  # noqa: E402
from vera.app.keystore import SessionKey  # noqa: E402
from vera.app.runs import RunManager  # noqa: E402
from vera.app.server import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BROWSERS = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    shutil.which("chromium") or "", shutil.which("google-chrome") or "",
]  # fmt: skip
BROWSER = next((b for b in BROWSERS if b and Path(b).exists()), None)
pytestmark = pytest.mark.skipif(BROWSER is None, reason="no headless Chrome or Edge found")


def fixture_run(
    root: Path, run_id: str, state: str, message: str | None, audit: str | None, findings: list | None = None
) -> None:
    run_dir = root / "runs" / run_id
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "app_request.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "topic": "A topic",
                "max_usd": 1.0,
                "max_wall_seconds": 3600,
                "guidance": {},
                "allow_experiments": False,
            }
        ),
        encoding="utf-8",
    )
    app_state.write(run_dir, state, message)
    if audit:
        (run_dir / "literature.md").write_text(
            "## Literature review\n\nA claim that is long enough to be dotted [R1].\n\n## References\n\n[R1] A. Author. A title. 2024.\n",
            encoding="utf-8",
        )
        (run_dir / "claims.jsonl").write_text(
            json.dumps(
                {
                    "claim": "A claim that is long enough to be dotted",
                    "source_key": "R1",
                    "quote": "the quote",
                    "locator": "abstract",
                    "quote_check": "pass",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "retrieved.jsonl").write_text(
            json.dumps(
                {
                    "key": "R1",
                    "title": "A title",
                    "authors": ["A. Author"],
                    "year": "2024",
                    "url": "https://example.org",
                    "id": "x",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "artifacts" / "audit_report.json").write_text(
            json.dumps({"overall": audit, "findings": findings or [], "checks_run": ["citation", "claim_support"]}),
            encoding="utf-8",
        )


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("uiroot")
    fixture_run(
        root, "done-run", "complete", None, "amber", [{"severity": "warn", "summary": "a lead", "check": "method_code"}]
    )
    fixture_run(
        root, "stopped-run", "stopped", "Stopped at your request. Everything done so far is kept; you can resume.", None
    )
    fixture_run(
        root,
        "budget-run",
        "stopped",
        "Stopped at your budget (budget: usd 1.01 > 1.0). The best result so far is kept.",
        None,
    )
    fixture_run(
        root,
        "red-run",
        "complete",
        None,
        "red",
        [{"severity": "fail", "summary": "a citation does not resolve", "check": "citation"}],
    )
    fixture_run(root, "wait-run", "awaiting_confirmation", "Check the question VERA proposes.", None)
    (root / "runs" / "wait-run" / "scope.json").write_text(
        json.dumps(
            {
                "topic_id": "wait-run",
                "question": "Does X hold?",
                "why_researchable": "w",
                "empirical": False,
                "candidate_parent": None,
                "no_parent_reason": "n",
                "status": "proposed",
            }
        ),
        encoding="utf-8",
    )
    session = SessionKey()
    app = create_app(
        ROOT,
        session=session,
        manager=RunManager(root, session, lambda *a: None),
        probes={"docker": lambda: False, "grobid": lambda: False},
    )
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield port
    srv.should_exit = True
    thread.join(timeout=5)


def dom(port: int, route: str) -> str:
    out = subprocess.run(
        [
            BROWSER,
            "--headless=old",
            "--disable-gpu",
            "--virtual-time-budget=8000",
            "--dump-dom",
            f"http://127.0.0.1:{port}/#/{route}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    return out.stdout


@pytest.mark.parametrize("route, must_have", [
    ("", "Whose key and whose money"),
    ("new", "Propose a question"),
    ("runs", "done-run"),
    ("run/done-run", "Read the review"),
    ("run/stopped-run", "Resume"),
    ("run/budget-run", "Stopped at your budget"),
    ("run/wait-run", "Confirm and continue"),
    ("read/done-run", "a lead, not a verdict"),
    ("read/red-run", "a citation does not resolve"),
    ("examples", "What went in"),
    ("example/tree-explain", "The audit"),
    ("example/conformal-shift", "Retrieval and its limits"),
])  # fmt: skip
def test_each_page_renders_against_fixture_runs(server: int, route: str, must_have: str) -> None:
    html = dom(server, route)
    assert "The app could not start" not in html and "Something went wrong" not in html, route
    assert must_have in html, f"{route}: expected {must_have!r}"
