# ruff: noqa: E501
"""The Pages showcase: built from committed files, relative paths, no key, no server, the known issues shown, and the pages render."""

from __future__ import annotations

import functools
import http.server
import json
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from scripts.build_pages import build  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BROWSERS = ["C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            shutil.which("chromium") or "", shutil.which("google-chrome") or ""]  # fmt: skip
BROWSER = next((b for b in BROWSERS if b and Path(b).exists()), None)


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("pages") / "VERA"  # served under a sub-path, as GitHub does for a project site
    build(out)
    return out


def test_the_site_is_static_relative_and_complete(site: Path) -> None:
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="app.css"' in html and 'src="static-config.js"' in html and 'src="app.js"' in html
    assert (
        "/static/" not in html and 'href="/' not in html and 'src="/' not in html
    )  # nothing absolute: the site lives under /VERA/
    assert (site / "static-config.js").read_text(encoding="utf-8").strip() == "window.VERA_STATIC = true;"
    assert (site / ".nojekyll").exists()
    facts = json.loads((site / "data" / "facts.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in facts["examples"]]
    assert len(ids) == 7 and {"agentic-traces-walkthrough", "rlm-vs-clm", "agent-traces-first"} <= set(ids)
    for i in ids:
        paper = json.loads((site / "data" / "examples" / i / "paper.json").read_text(encoding="utf-8"))
        assert paper["markdown"] and paper["claims"] is not None and paper["example"]["id"] == i
        pdf = (site / "pdf" / f"{i}.pdf").read_bytes()
        assert pdf[:5] == b"%PDF-" and len(pdf) > 20_000
    assert (site / "data" / "examples" / "tree-explain" / "files" / "figures" / "fig_rank_stability.png").exists()
    assert (site / "data" / "examples" / "tree-explain" / "files" / "results.json").exists()


def test_the_three_reviews_with_findings_carry_them_and_the_audited_four_do_not_invent_any(site: Path) -> None:
    facts = {e["id"]: e for e in json.loads((site / "data" / "facts.json").read_text(encoding="utf-8"))["examples"]}
    assert (
        "R12" in facts["agentic-traces-walkthrough"]["known_issues"]
        and "Tracezip" in facts["agentic-traces-walkthrough"]["known_issues"]
    )
    assert "supplied abstract" in facts["rlm-vs-clm"]["known_issues"] and "65%" in facts["rlm-vs-clm"]["known_issues"]
    assert "part of the question" in facts["agent-traces-first"]["known_issues"]
    assert all(
        facts[i]["known_issues"] is None
        for i in ("conformal-shift", "research-agents-eval", "tree-explain", "credal-dro")
    )
    assert all(e["audit"] in {"green", "amber", "red"} and e["topic"] and e["question"] for e in facts.values())


def test_nothing_secret_or_dynamic_is_published(site: Path) -> None:
    keys = [re.compile("sk-" + r"or-v1-[0-9a-f]{32,}"), re.compile("sk-" + r"ant-[A-Za-z0-9_-]{20,}")]
    for p in site.rglob("*"):
        if p.is_file() and p.suffix in {".json", ".js", ".html", ".css"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            assert not any(k.search(text) for k in keys), p.name
    js = (site / "app.js").read_text(encoding="utf-8")
    assert (
        "VERA_STATIC" in js
        and 'STATIC ? "" : el("div", { class: "row" }, el("button", { type: "button", onclick: openKeyDialog }' in js
    )  # no key box in static mode
    assert not (site / "api").exists()  # no server-side routes were built


@pytest.fixture(scope="module")
def served(site: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site.parent))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def dom(port: int, route: str, tmp_path: Path) -> str:
    for attempt in range(2):
        profile = tmp_path / f"profile-{route.replace('/', '_') or 'home'}-{attempt}"
        try:
            out = subprocess.run([BROWSER, "--headless=old", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run", "--virtual-time-budget=8000", "--dump-dom", f"http://127.0.0.1:{port}/VERA/index.html#/{route}"],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False)  # fmt: skip
        except subprocess.TimeoutExpired:
            continue
        if out.stdout:
            return out.stdout
    return ""


@pytest.mark.skipif(BROWSER is None, reason="no headless Chrome or Edge found")
@pytest.mark.parametrize("route, must_have, must_not", [
    ("", "Read-only showcase", "Connect my key"),
    ("examples", "Known issues.", "The app could not start"),
    ("example/rlm-vs-clm", "Download PDF", "Something went wrong"),
    ("example/tree-explain", 'class="cite"', "The app could not start"),
    ("run-locally", "uv run vera-app", "Propose a question"),
    ("new", "VERA runs on your own computer", "Propose a question"),  # a run-form route redirects to the run-it-yourself page
    ("runs", "VERA runs on your own computer", "My runs"),
])  # fmt: skip
def test_the_static_pages_render_under_a_subpath(
    served: int, route: str, must_have: str, must_not: str, tmp_path: Path
) -> None:
    html = dom(served, route, tmp_path)
    assert must_have in html, f"{route}: expected {must_have!r}"
    assert must_not not in html, f"{route}: found {must_not!r}"
