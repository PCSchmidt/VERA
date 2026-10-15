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
    fixture_run(root, "disagree-run", "complete", None, "amber",  # Increment 8 (AUD-F-13): a judge disagreement
                [{"severity": "warn", "check": "sentence",
                  "summary": "judges disagree (passed at write time, yes on jev at 0.71; failed in the audit, no on glm-flash at 0.98): S76"}])  # fmt: skip
    fixture_run(root, "unsettled-run", "complete", None, "amber",  # Increment 9 (AUD-F-14): the reference was unsure
                [{"severity": "warn", "check": "sentence",
                  "summary": "unsettled (the reference judge was unsure (no on sonnet-ref at 0.62)): S4"}])  # fmt: skip
    fixture_run(root, "paper-run", "complete", None, "green")  # a review with a finished paper (Increment 6)
    from tests.test_app_paper import written_paper  # noqa: PLC0415

    written_paper(root / "runs" / "paper-run")
    (root / "runs" / "paper-run" / "paper" / "app_paper_request.json").write_text(
        json.dumps({"request": {"max_usd": 0.75, "length_words": 3000, "emphasis": None}, "spent_before_usd": 0.0}),
        encoding="utf-8",
    )
    app_state.write(root / "runs" / "paper-run" / "paper", "complete", None)
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


def dom(port: int, route: str, tmp_path: Path) -> str:
    """The page's DOM after its scripts ran. A fresh browser profile per load (a shared one can hang on a lock), one retry."""
    for attempt in range(2):
        profile = tmp_path / f"profile-{route.replace('/', '_') or 'home'}-{attempt}"
        try:
            out = subprocess.run(
                [BROWSER, "--headless=old", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                 "--virtual-time-budget=8000", "--dump-dom", f"http://127.0.0.1:{port}/#/{route}"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False,
            )  # fmt: skip
        except subprocess.TimeoutExpired:
            continue
        if out.stdout:
            return out.stdout
    return ""


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
    ("example/conformal-shift", 'class="ref"'),
    ("example/conformal-shift", "Download PDF"),
    ("run/done-run", "Download PDF"),
    ("read/done-run", "Make a paper from this review"),
    ("make-paper/done-run", "not checked against quotes"),
    ("run/paper-run", "Make a paper from this review"),
    ("paper-run/paper-run", "Read the paper"),
    ("paper/paper-run", 'class="interp"'),
    ("paper/paper-run", 'class="premise"'),
    ("paper/paper-run", "Review paper"),
    ("paper/paper-run", "1 kept, 1 removed by the checks"),
    ("read/paper-run", 'class="tabs"'),
    ("paper/paper-run", 'class="synth"'),  # Increment 7: a synthesis sentence is marked, with its premises
    ("paper/paper-run", "1 synthesis kept, 0 removed by the checks"),
    ("read/disagree-run", 'class="disagree"'),  # Increment 8: judge disagreements listed apart
    ("read/disagree-run", "Judge disagreements (1)"),
    ("read/unsettled-run", 'class="unsettled"'),  # Increment 9: unsettled items listed apart
])  # fmt: skip
def test_each_page_renders_against_fixture_runs(server: int, route: str, must_have: str, tmp_path: Path) -> None:
    html = dom(server, route, tmp_path)
    assert "The app could not start" not in html and "Something went wrong" not in html, route
    assert must_have in html, f"{route}: expected {must_have!r}"
